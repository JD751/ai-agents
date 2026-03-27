import hashlib
import logging
import os
import tempfile
from pathlib import Path

import azure.functions as func
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

app = func.FunctionApp()

_TEXT_SUFFIXES = {".txt", ".md"}
_COLLECTION = "bayer-rag"  # must match rag_service.py


def _chunk_id(source: str, index: int, content: str) -> str:
    """Deterministic ID — must match the logic in rag_service.py for deduplication."""
    key = f"{source}:{index}:{content[:64]}"
    return hashlib.md5(key.encode()).hexdigest()


def _parse_blob(blob_name: str, content: bytes) -> list[Document]:
    """Parse blob bytes into LangChain Documents based on file extension."""
    suffix = Path(blob_name).suffix.lower()

    if suffix in _TEXT_SUFFIXES:
        text = content.decode("utf-8", errors="ignore")
        return [Document(page_content=text, metadata={"source": blob_name})]

    if suffix == ".pdf":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            reader = PdfReader(tmp_path)
            return [
                Document(
                    page_content=page.extract_text() or "",
                    metadata={"source": blob_name, "page": i},
                )
                for i, page in enumerate(reader.pages)
            ]
        finally:
            os.unlink(tmp_path)

    logging.warning("Unsupported file type — skipping: %s", blob_name)
    return []


def _get_vector_store() -> Chroma:
    """Build a Chroma client pointed at the external ChromaDB Container App."""
    chroma_host = os.environ["CHROMA_HOST"]
    chroma_token = os.environ["CHROMA_AUTH_TOKEN"]
    embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key = os.environ["OPENAI_API_KEY"]

    host = chroma_host.removeprefix("https://").removeprefix("http://")
    ssl = chroma_host.startswith("https://")
    client = chromadb.HttpClient(
        host=host,
        port=443 if ssl else 8000,
        ssl=ssl,
        headers={"Authorization": f"Bearer {chroma_token}"},
    )
    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=openai_api_key)

    return Chroma(
        client=client,
        collection_name=_COLLECTION,
        embedding_function=embeddings,
    )


@app.blob_trigger(
    arg_name="myblob",
    path="bayer-ai-documents/{name}",
    connection="BlobStorageConnection",
)
def ingest_blob(myblob: func.InputStream) -> None:
    blob_name = myblob.name.split("/")[-1]
    logging.info("Blob trigger fired: %s (%d bytes)", blob_name, myblob.length)

    content = myblob.read()
    docs = _parse_blob(blob_name, content)

    if not docs:
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    ids = [_chunk_id(blob_name, i, c.page_content) for i, c in enumerate(chunks)]

    vector_store = _get_vector_store()

    existing_ids = set(vector_store.get(ids=ids)["ids"])
    new_chunks = [c for c, i in zip(chunks, ids) if i not in existing_ids]
    new_ids = [i for i in ids if i not in existing_ids]

    if new_chunks:
        vector_store.add_documents(documents=new_chunks, ids=new_ids)
        logging.info(
            "Ingestion complete — blob: %s, chunks added: %d, skipped: %d",
            blob_name,
            len(new_chunks),
            len(chunks) - len(new_chunks),
        )
    else:
        logging.info("All chunks already in vector store — blob: %s", blob_name)
