from pydantic import field_validator
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
    chroma_host: str = ""  # set to "chroma" in Docker; empty = use PersistentClient
    chroma_port: int = 8000

    # Production hardening
    request_timeout_seconds: float = 30.0
    queue_max_size: int = 100
    queue_workers: int = 2
    rate_limit_default: str = "60/minute"
    rate_limit_agent: str = "10/minute"
    rate_limit_ask: str = "30/minute"
    rate_limit_draft: str = "20/minute"
    rate_limit_review: str = "20/minute"
    rate_limit_ingest: str = "5/minute"

    # PostgreSQL
    database_url: str = (
        "postgresql+asyncpg://bayeruser:bayerpass@localhost:5432/bayerai"
    )

    # LangSmith tracing
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "bayer-ai"
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"

    @field_validator("langchain_tracing_v2", mode="before")
    @classmethod
    def strip_bool_whitespace(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", str_strip_whitespace=True
    )
