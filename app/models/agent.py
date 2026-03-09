from pydantic import BaseModel


class AgentRequest(BaseModel):
    query: str
    thread_id: str = "default"


class AgentResponse(BaseModel):
    answer: str
    tool_calls: list[str]
    citations: list[str]
