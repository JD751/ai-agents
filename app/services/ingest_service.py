import asyncio
from dataclasses import dataclass

from langchain_chroma import Chroma

from app.config.settings import Settings
from app.core.logging import get_logger
from app.services.rag_ingest import load_documents

logger = get_logger(__name__)


@dataclass
class IngestResult:
    chunks_added: int
    files_processed: int


class IngestService:
    def __init__(self, vector_store: Chroma, settings: Settings):
        self._vector_store = vector_store
        self._settings = settings

    def ingest(self) -> IngestResult:
        """Scan documents_dir, chunk all files, upsert into Chroma. Skips already-stored chunks."""
        chunks, ids = load_documents(self._settings.documents_dir, self._settings)

        if not chunks:
            logger.info("No documents found to ingest")
            return IngestResult(chunks_added=0, files_processed=0)

        # Chroma upserts by ID — existing chunks are skipped, new ones are added
        existing_ids = set(self._vector_store.get(ids=ids)["ids"])
        new_chunks = [c for c, i in zip(chunks, ids) if i not in existing_ids]
        new_ids = [i for i in ids if i not in existing_ids]

        if new_chunks:
            self._vector_store.add_documents(documents=new_chunks, ids=new_ids)
            logger.info(
                "Ingestion complete",
                extra={"chunks_added": len(new_chunks), "chunks_skipped": len(chunks) - len(new_chunks)},
            )
        else:
            logger.info("All chunks already in vector store — nothing to add")

        files_processed = len({c.metadata.get("source", "unknown") for c in chunks})
        return IngestResult(chunks_added=len(new_chunks), files_processed=files_processed)

    async def ingest_async(self) -> IngestResult:
        return await asyncio.to_thread(self.ingest)
