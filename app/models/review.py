from pydantic import BaseModel


class ReviewRequest(BaseModel):
    text: str


class ReviewResponse(BaseModel):
    is_compliant: bool
    notes: list[str]
