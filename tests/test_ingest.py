from app.services.rag_ingest import load_documents

docs = load_documents("documents")
print(f"Loaded {len(docs)} chunks")

print(docs[0].page_content[:200])