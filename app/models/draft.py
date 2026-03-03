from pydantic import BaseModel

class DraftRequest(BaseModel):
    brief: str

class DraftResponse(BaseModel):
    draft: str