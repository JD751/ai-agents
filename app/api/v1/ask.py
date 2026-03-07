from fastapi import APIRouter, Depends, Request

from app.api.deps import get_rag_service, get_settings
from app.core.limiter import limiter
from app.core.validators import validate_ask_response
from app.models.ask import AskRequest, AskResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
@limiter.limit(lambda: get_settings().rate_limit_ask)
def ask(request: Request, payload: AskRequest, rag: RAGService = Depends(get_rag_service)):
    result = rag.answer(payload.question, request_id=request.state.request_id)
    validate_ask_response(result.answer)
    return AskResponse(answer=result.answer, citations=result.citations)
