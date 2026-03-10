import hashlib
from pathlib import Path

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TEXT_SUFFIXES = {".txt", ".md"}


def _chunk_id(source: str, index: int, content: str) -> str:
    """Deterministic ID based on source path, chunk position, and content."""
    key = f"{source}:{index}:{content[:64]}"
    return hashlib.md5(key.encode()).hexdigest()


def load_documents(
    documents_dir: str, settings: Settings | None = None
) -> tuple[list[Document], list[str]]:
    """Load and chunk documents, returning (chunks, ids) for upsert into a vector store."""
    if settings is None:
        settings = Settings()

    dir_path = Path(documents_dir)
    if not dir_path.exists():
        raise ValueError(f"Documents directory does not exist: {dir_path}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    docs = []
    for file in dir_path.rglob("*"):
        if not file.is_file():
            continue
        try:
            if file.suffix in _TEXT_SUFFIXES:
                text = file.read_text(encoding="utf-8", errors="ignore")
                loaded = [Document(page_content=text, metadata={"source": str(file)})]
            elif file.suffix == ".pdf":
                reader = PdfReader(str(file))
                loaded = [
                    Document(
                        page_content=page.extract_text() or "",
                        metadata={"source": str(file), "page": i},
                    )
                    for i, page in enumerate(reader.pages)
                ]
            else:
                logger.debug("Skipping unsupported file", extra={"file": str(file)})
                continue

            docs.extend(loaded)
            logger.info(
                "Loaded document", extra={"file": str(file), "pages": len(loaded)}
            )

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            logger.error(
                "Failed to load document",
                extra={"file": str(file), "error": str(exc)},
                exc_info=True,
            )

    chunks = splitter.split_documents(docs)
    ids = [
        _chunk_id(
            chunk.metadata.get("source", "unknown"),
            index,
            chunk.page_content,
        )
        for index, chunk in enumerate(chunks)
    ]

    logger.info(
        "Ingestion complete",
        extra={"total_docs": len(docs), "total_chunks": len(chunks)},
    )
    return chunks, ids
