from pydantic import BaseModel


class IngestResponse(BaseModel):
    chunks_added: int
    files_processed: int
