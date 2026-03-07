import asyncio

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_review_service, get_settings
from app.core.limiter import limiter
from app.core.validators import validate_review_response
from app.models.review import ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter()


@router.post("/review", response_model=ReviewResponse)
@limiter.limit(lambda: get_settings().rate_limit_review)
async def review(
    request: Request,
    payload: ReviewRequest,
    review_service: ReviewService = Depends(get_review_service),
):
    rid = request.state.request_id
    result = await asyncio.to_thread(lambda: review_service.review(payload.text, request_id=rid))
    validate_review_response(result.notes)
    return ReviewResponse(is_compliant=result.is_compliant, notes=result.notes)
