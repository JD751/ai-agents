import re
from dataclasses import dataclass, field

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.logging import get_logger
from app.core.retry import llm_retry

logger = get_logger(__name__)

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a regulatory compliance reviewer for Bayer consumer health products. "
            "Using only the compliance policy documents provided as context, evaluate whether "
            "the submitted marketing text is compliant.\n\n"
            "Respond in exactly this format:\n"
            "VERDICT: COMPLIANT or NON-COMPLIANT\n"
            "NOTES:\n"
            "- <note 1>\n"
            "- <note 2>\n\n"
            "Each note must reference a specific policy or claim. "
            "If compliant, notes should confirm which policies are satisfied.\n\n"
            "Context:\n{context}",
        ),
        ("human", "Marketing text to review:\n{text}"),
    ]
)


@dataclass
class ReviewResult:
    is_compliant: bool
    notes: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)


class ReviewService:
    def __init__(self, retriever, chain):
        self._retriever = retriever
        self._chain = chain

    @classmethod
    async def create(
        cls,
        vector_store: Chroma,
        openai_api_key: str,
        chat_model: str,
        retrieval_k: int,
        llm_temperature: float,
    ) -> "ReviewService":
        retriever = vector_store.as_retriever(search_kwargs={"k": retrieval_k})
        llm = ChatOpenAI(
            model=chat_model, api_key=openai_api_key, temperature=llm_temperature
        )
        chain = _PROMPT | llm
        logger.info("Review service initialised")
        return ReviewService(retriever=retriever, chain=chain)

    def review(self, text: str, request_id: str = "unknown") -> ReviewResult:
        docs = self._retriever.invoke(text)
        context = "\n\n".join(doc.page_content for doc in docs)
        citations = list(
            dict.fromkeys(doc.metadata.get("source", "unknown") for doc in docs)
        )

        @llm_retry
        def _invoke():
            return self._chain.invoke(
                {"text": text, "context": context},
                config={"metadata": {"request_id": request_id}},
            )

        response = _invoke()
        result = _parse_response(response.content)
        result.citations = citations
        return result


def _parse_response(content: str) -> ReviewResult:
    is_compliant = bool(re.search(r"VERDICT:\s*COMPLIANT\b", content, re.IGNORECASE))
    notes = re.findall(r"^[-•]\s*(.+)$", content, re.MULTILINE)
    return ReviewResult(is_compliant=is_compliant, notes=notes or [content.strip()])
