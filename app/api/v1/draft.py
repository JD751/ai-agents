import asyncio
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_draft_service, get_settings
from app.core.limiter import limiter
from app.core.validators import validate_draft_response
from app.db.models import QueryLog
from app.models.draft import DraftRequest, DraftResponse
from app.services.draft_service import DraftService

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
@limiter.limit(lambda: get_settings().rate_limit_draft)
async def draft(
    request: Request,
    payload: DraftRequest,
    draft_service: DraftService = Depends(get_draft_service),
    db: AsyncSession = Depends(get_db),
):
    rid = request.state.request_id
    start = time.monotonic()
    result = await asyncio.to_thread(
        lambda: draft_service.draft(payload.brief, request_id=rid)
    )
    latency_ms = (time.monotonic() - start) * 1000

    validate_draft_response(result.draft)

    db.add(
        QueryLog(
            request_id=rid,
            endpoint="/draft",
            input_text=payload.brief,
            response_text=result.draft,
            citation_count=len(result.citations),
            latency_ms=round(latency_ms, 2),
        )
    )
    await db.commit()

    return DraftResponse(draft=result.draft, citations=result.citations)
