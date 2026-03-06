import asyncio

from fastapi import APIRouter, Depends

from app.api.deps import get_draft_service
from app.models.draft import DraftRequest, DraftResponse
from app.services.draft_service import DraftService

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
async def draft(
    payload: DraftRequest,
    draft_service: DraftService = Depends(get_draft_service),
):
    result = await asyncio.to_thread(draft_service.draft, payload.brief)
    return DraftResponse(draft=result.draft, citations=result.citations)