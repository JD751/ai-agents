from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.api.root import router as root_router
from app.api.deps import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    settings = get_settings()

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

    app.state.agent = BayerAgent.create(
        rag_service=app.state.rag_service,
        draft_service=app.state.draft_service,
        review_service=app.state.review_service,
        openai_api_key=settings.openai_api_key,
        chat_model=settings.chat_model,
    )
    logger.info("Bayer agent initialised", extra={"event": "agent_ready"})

    yield

    logger.info("Application shutdown", extra={"event": "shutdown"})


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.include_router(root_router)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
