import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import router as v1_router
from app.api.root import router as root_router
from app.api.deps import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    RequestIDMiddleware,
    TimeoutMiddleware,
    global_exception_handler,
)
from app.core.limiter import limiter
from app.db.base import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    init_db(settings.database_url)
    logger.info("Database initialised", extra={"event": "db_ready"})

    if settings.langchain_tracing_v2:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
        logger.info(
            "LangSmith tracing enabled", extra={"project": settings.langchain_project}
        )

    logger.info("Application startup", extra={"event": "startup"})

    from app.agents.agent import BayerAgent
    from app.services.rag_service import RAGService
    from app.services.draft_service import DraftService
    from app.services.ingest_service import IngestService
    from app.services.review_service import ReviewService

    app.state.rag_service = await RAGService.create(
        openai_api_key=settings.openai_api_key,
        embedding_model=settings.embedding_model,
        chat_model=settings.chat_model,
        retrieval_k=settings.retrieval_k,
        llm_temperature=settings.llm_temperature,
        settings=settings,
    )
    logger.info("RAG service initialised", extra={"event": "rag_ready"})

    app.state.draft_service = await DraftService.create(
        vector_store=app.state.rag_service.vector_store,
        openai_api_key=settings.openai_api_key,
        chat_model=settings.chat_model,
        retrieval_k=settings.retrieval_k,
        llm_temperature=settings.llm_temperature,
    )
    logger.info("Draft service initialised", extra={"event": "draft_ready"})

    app.state.ingest_service = IngestService(
        vector_store=app.state.rag_service.vector_store,
        settings=settings,
    )
    logger.info("Ingest service initialised", extra={"event": "ingest_ready"})

    app.state.review_service = await ReviewService.create(
        vector_store=app.state.rag_service.vector_store,
        openai_api_key=settings.openai_api_key,
        chat_model=settings.chat_model,
        retrieval_k=settings.retrieval_k,
        llm_temperature=settings.llm_temperature,
    )
    logger.info("Review service initialised", extra={"event": "review_ready"})

    app.state.agent = await BayerAgent.create(
        rag_service=app.state.rag_service,
        draft_service=app.state.draft_service,
        review_service=app.state.review_service,
        openai_api_key=settings.openai_api_key,
        chat_model=settings.chat_model,
        database_url=settings.database_url,
    )
    logger.info("Bayer agent initialised", extra={"event": "agent_ready"})

    yield

    await app.state.agent.close()
    logger.info("Application shutdown", extra={"event": "shutdown"})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Middleware — LIFO: last registered = first executed
    # TimeoutMiddleware registered first so RequestIDMiddleware runs before it
    app.add_middleware(TimeoutMiddleware, timeout=settings.request_timeout_seconds)
    app.add_middleware(RequestIDMiddleware)  # runs first on every request

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    app.include_router(root_router)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
