import asyncio
from dataclasses import dataclass
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config.settings import Settings
from app.core.logging import get_logger
from app.services.rag_ingest import load_documents

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


def _build_vector_store(
    persist_dir: str,
    embeddings: OpenAIEmbeddings,
    chunks: list[Document],
    ids: list[str],
) -> Chroma:
    """Load existing Chroma DB from disk, or create and populate it."""
    client = chromadb.PersistentClient(path=persist_dir)
    existing = set(client.list_collections())

    vector_store = Chroma(
        client=client,
        collection_name=_COLLECTION,
        embedding_function=embeddings,
    )

    if _COLLECTION not in existing or client.get_collection(_COLLECTION).count() == 0:
        logger.info("No existing vector store found — ingesting documents")
        vector_store.add_documents(documents=chunks, ids=ids)
        logger.info("Vector store created", extra={"persist_dir": persist_dir, "chunks": len(chunks)})
    else:
        logger.info(
            "Loaded existing vector store from disk",
            extra={"persist_dir": persist_dir},
        )

    return vector_store


class RAGService:
    def __init__(self, retriever, chain):
        self._retriever = retriever
        self._chain = chain

    @classmethod
    async def create(
        cls,
        documents_dir: str,
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
        persist_dir = str(Path(settings.chroma_persist_dir).resolve())

        # Only load documents if we need to ingest (checked inside _build_vector_store)
        chunks, ids = await asyncio.to_thread(load_documents, documents_dir, settings)

        vector_store = await asyncio.to_thread(
            _build_vector_store, persist_dir, embeddings, chunks, ids
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": retrieval_k})

        llm = ChatOpenAI(model=chat_model, api_key=openai_api_key, temperature=llm_temperature)
        chain = _PROMPT | llm

        return RAGService(retriever=retriever, chain=chain)

    def answer(self, question: str) -> AskResult:
        docs = self._retriever.invoke(question)

        context = "\n\n".join(doc.page_content for doc in docs)
        citations = [doc.metadata.get("source", "unknown") for doc in docs]

        response = self._chain.invoke({"question": question, "context": context})

        return AskResult(answer=response.content, citations=list(dict.fromkeys(citations)))
