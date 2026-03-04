from pathlib import Path
from langchain.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def load_documents(documents_dir: str):
    docs = []

    for file in Path(documents_dir).glob("*"):
        if file.suffix == ".txt":
            docs.extend(TextLoader(str(file)).load())

        if file.suffix == ".md":
            docs.extend(TextLoader(str(file)).load())

        if file.suffix == ".pdf":
            docs.extend(PyPDFLoader(str(file)).load())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    return splitter.split_documents(docs)