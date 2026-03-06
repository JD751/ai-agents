from functools import lru_cache

from fastapi import Request

from app.agents.agent import BayerAgent
from app.config.settings import Settings
from app.services.draft_service import DraftService
from app.services.ingest_service import IngestService
from app.services.rag_service import RAGService
from app.services.review_service import ReviewService


@lru_cache
def get_settings() -> Settings:
    # Cached so we don't rebuild settings every request
    return Settings()


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_draft_service(request: Request) -> DraftService:
    return request.app.state.draft_service


def get_ingest_service(request: Request) -> IngestService:
    return request.app.state.ingest_service


def get_review_service(request: Request) -> ReviewService:
    return request.app.state.review_service


def get_agent(request: Request) -> BayerAgent:
    return request.app.state.agent