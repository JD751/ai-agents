from fastapi import APIRouter, Depends

from app.api.deps import get_rag_service
from app.models.ask import AskRequest, AskResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, rag: RAGService = Depends(get_rag_service)):
    result = rag.answer(payload.question)
    return AskResponse(answer=result.answer, citations=result.citations)
