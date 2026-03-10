import asyncio
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_rag_service, get_settings
from app.core.limiter import limiter
from app.core.validators import validate_ask_response
from app.db.models import QueryLog
from app.models.ask import AskRequest, AskResponse
from app.services.rag_service import RAGService

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
@limiter.limit(lambda: get_settings().rate_limit_ask)
async def ask(
    request: Request,
    payload: AskRequest,
    rag: RAGService = Depends(get_rag_service),
    db: AsyncSession = Depends(get_db),
):
    start = time.monotonic()
    result = await asyncio.to_thread(
        rag.answer, payload.question, request.state.request_id
    )
    latency_ms = (time.monotonic() - start) * 1000

    validate_ask_response(result.answer)

    db.add(
        QueryLog(
            request_id=request.state.request_id,
            endpoint="/ask",
            input_text=payload.question,
            response_text=result.answer,
            citation_count=len(result.citations),
            latency_ms=round(latency_ms, 2),
        )
    )
    await db.commit()

    return AskResponse(answer=result.answer, citations=result.citations)
