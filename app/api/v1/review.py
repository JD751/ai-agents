import asyncio
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_review_service, get_settings
from app.core.limiter import limiter
from app.core.validators import validate_review_response
from app.db.models import QueryLog
from app.models.review import ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter()


@router.post("/review", response_model=ReviewResponse)
@limiter.limit(lambda: get_settings().rate_limit_review)
async def review(
    request: Request,
    payload: ReviewRequest,
    review_service: ReviewService = Depends(get_review_service),
    db: AsyncSession = Depends(get_db),
):
    rid = request.state.request_id
    start = time.monotonic()
    result = await asyncio.to_thread(
        lambda: review_service.review(payload.text, request_id=rid)
    )
    latency_ms = (time.monotonic() - start) * 1000

    validate_review_response(result.notes)

    db.add(
        QueryLog(
            request_id=rid,
            endpoint="/review",
            input_text=payload.text,
            response_text="\n".join(result.notes),
            citation_count=0,
            is_compliant=result.is_compliant,
            latency_ms=round(latency_ms, 2),
        )
    )
    await db.commit()

    return ReviewResponse(is_compliant=result.is_compliant, notes=result.notes)
