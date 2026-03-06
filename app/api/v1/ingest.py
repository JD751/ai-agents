from fastapi import APIRouter, Depends

from app.api.deps import get_ingest_service
from app.models.ingest import IngestResponse
from app.services.ingest_service import IngestService

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(ingest_service: IngestService = Depends(get_ingest_service)):
    result = await ingest_service.ingest_async()
    return IngestResponse(chunks_added=result.chunks_added, files_processed=result.files_processed)
