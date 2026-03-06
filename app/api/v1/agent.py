from fastapi import APIRouter, Depends

from app.agents.agent import BayerAgent
from app.api.deps import get_agent
from app.models.agent import AgentRequest, AgentResponse

router = APIRouter()


@router.post("/agent", response_model=AgentResponse)
async def run_agent(
    body: AgentRequest,
    agent: BayerAgent = Depends(get_agent),
) -> AgentResponse:
    result = await agent.run(query=body.query, thread_id=body.thread_id)
    return AgentResponse(answer=result.answer, tool_calls=result.tool_calls)
