import asyncio
from dataclasses import dataclass
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config.settings import Settings
from app.core.logging import get_logger
from app.core.retry import llm_retry

logger = get_logger(__name__)

_COLLECTION = "bayer-rag"

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a helpful assistant for Bayer consumer health. "
        "Answer the question using only the context below. "
        "Be concise and factual. "
        "If the answer is not in the context, say you don't know.\n\n"
        "Context:\n{context}",
    ),
    ("human", "{question}"),
])


@dataclass
class AskResult:
    answer: str
    citations: list[str]


def build_vector_store(settings: Settings, embeddings: OpenAIEmbeddings) -> Chroma:
    """Connect to (or create) the persistent Chroma collection. Never ingests documents.

    Uses HttpClient when CHROMA_HOST is configured (Docker / production).
    Falls back to PersistentClient for local development outside Docker.
    """
    if settings.chroma_host:
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        logger.info("Connected to Chroma via HTTP", extra={"host": settings.chroma_host, "port": settings.chroma_port})
    else:
        persist_dir = str(Path(settings.chroma_persist_dir).resolve())
        client = chromadb.PersistentClient(path=persist_dir)
        logger.info("Connected to Chroma via PersistentClient", extra={"persist_dir": persist_dir})

    return Chroma(
        client=client,
        collection_name=_COLLECTION,
        embedding_function=embeddings,
    )


class RAGService:
    def __init__(self, retriever, chain, vector_store: Chroma):
        self._retriever = retriever
        self._chain = chain
        self.vector_store = vector_store

    @classmethod
    async def create(
        cls,
        openai_api_key: str,
        embedding_model: str,
        chat_model: str,
        retrieval_k: int,
        llm_temperature: float,
        settings: Settings | None = None,
    ) -> "RAGService":
        if settings is None:
            settings = Settings()

        embeddings = OpenAIEmbeddings(model=embedding_model, api_key=openai_api_key)

        vector_store = await asyncio.to_thread(build_vector_store, settings, embeddings)
        retriever = vector_store.as_retriever(search_kwargs={"k": retrieval_k})

        llm = ChatOpenAI(model=chat_model, api_key=openai_api_key, temperature=llm_temperature)
        chain = _PROMPT | llm

        return RAGService(retriever=retriever, chain=chain, vector_store=vector_store)

    def answer(self, question: str, request_id: str = "unknown") -> AskResult:
        docs = self._retriever.invoke(question)

        context = "\n\n".join(doc.page_content for doc in docs)
        citations = [doc.metadata.get("source", "unknown") for doc in docs]

        @llm_retry
        def _invoke():
            return self._chain.invoke(
                {"question": question, "context": context},
                config={"metadata": {"request_id": request_id}},
            )

        response = _invoke()
        return AskResult(answer=response.content, citations=list(dict.fromkeys(citations)))
