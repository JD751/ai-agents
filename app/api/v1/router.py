from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.ask import router as ask_router
from app.api.v1.draft import router as draft_router
from app.api.v1.review import router as review_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.agent import router as agent_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(ingest_router, tags=["ingest"])
router.include_router(ask_router, tags=["ask"])
router.include_router(draft_router, tags=["draft"])
router.include_router(review_router, tags=["review"])
router.include_router(agent_router, tags=["agent"])