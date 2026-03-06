import asyncio
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a marketing copywriter for Bayer consumer health products. "
        "Using only the context provided, write compliant marketing copy based on the brief. "
        "The copy must be factual, grounded in the context, and must not make unsupported claims.\n\n"
        "Structure your response as:\n"
        "Headline: <one line>\n"
        "Body: <2-3 sentences>\n"
        "CTA: <call to action>\n\n"
        "Context:\n{context}",
    ),
    ("human", "Brief: {brief}"),
])


@dataclass
class DraftResult:
    draft: str
    citations: list[str]


class DraftService:
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
    ) -> "DraftService":
        retriever = vector_store.as_retriever(search_kwargs={"k": retrieval_k})
        llm = ChatOpenAI(model=chat_model, api_key=openai_api_key, temperature=llm_temperature)
        chain = _PROMPT | llm
        logger.info("Draft service initialised")
        return DraftService(retriever=retriever, chain=chain)

    def draft(self, brief: str) -> DraftResult:
        docs = self._retriever.invoke(brief)
        context = "\n\n".join(doc.page_content for doc in docs)
        citations = list(dict.fromkeys(doc.metadata.get("source", "unknown") for doc in docs))
        response = self._chain.invoke({"brief": brief, "context": context})
        return DraftResult(draft=response.content, citations=citations)
