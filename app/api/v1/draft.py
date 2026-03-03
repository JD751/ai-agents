from fastapi import APIRouter
from app.models.draft import DraftRequest, DraftResponse

router = APIRouter()

@router.post("/draft", response_model=DraftResponse)
def draft(payload: DraftRequest):
    return DraftResponse(draft="stub")