import asyncio

from fastapi import APIRouter, Depends

from app.api.deps import get_review_service
from app.models.review import ReviewRequest, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter()


@router.post("/review", response_model=ReviewResponse)
async def review(
    payload: ReviewRequest,
    review_service: ReviewService = Depends(get_review_service),
):
    result = await asyncio.to_thread(review_service.review, payload.text)
    return ReviewResponse(is_compliant=result.is_compliant, notes=result.notes)
