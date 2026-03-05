from functools import lru_cache

from fastapi import Request

from app.config.settings import Settings
from app.services.rag_service import RAGService


@lru_cache
def get_settings() -> Settings:
    # Cached so we don't rebuild settings every request
    return Settings()


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service