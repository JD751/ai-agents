from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "bayer-ai"
    documents_dir: str = "documents"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    retrieval_k: int = 4
    llm_temperature: float = 0.0
    chunk_size: int = 500
    chunk_overlap: int = 50
    chroma_persist_dir: str = "chroma_db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

