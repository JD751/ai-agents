from fastapi import APIRouter
from app.models.review import ReviewRequest, ReviewResponse

router = APIRouter()

@router.post("/review", response_model=ReviewResponse)
def review(payload: ReviewRequest):
    return ReviewResponse(is_compliant=False, notes=["stub"])