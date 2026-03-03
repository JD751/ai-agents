from fastapi import APIRouter, Depends
from app.api.deps import get_settings
from app.config.settings import Settings
from app.models.ask import AskRequest, AskResponse

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, settings: Settings = Depends(get_settings)):
    # Stub for Day 1. Real RAG comes Day 3.
    return AskResponse(answer="stub", citations=[])