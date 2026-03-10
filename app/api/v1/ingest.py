from fastapi import APIRouter, Depends, Request

from app.api.deps import get_ingest_service, get_settings
from app.core.limiter import limiter
from app.models.ingest import IngestResponse
from app.services.ingest_service import IngestService

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit(lambda: get_settings().rate_limit_ingest)
async def ingest(
    request: Request, ingest_service: IngestService = Depends(get_ingest_service)
):
    result = await ingest_service.ingest_async()
    return IngestResponse(
        chunks_added=result.chunks_added, files_processed=result.files_processed
    )
