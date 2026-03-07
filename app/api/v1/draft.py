import asyncio

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_draft_service, get_settings
from app.core.limiter import limiter
from app.core.validators import validate_draft_response
from app.models.draft import DraftRequest, DraftResponse
from app.services.draft_service import DraftService

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
@limiter.limit(lambda: get_settings().rate_limit_draft)
async def draft(
    request: Request,
    payload: DraftRequest,
    draft_service: DraftService = Depends(get_draft_service),
):
    rid = request.state.request_id
    result = await asyncio.to_thread(lambda: draft_service.draft(payload.brief, request_id=rid))
    validate_draft_response(result.draft)
    return DraftResponse(draft=result.draft, citations=result.citations)