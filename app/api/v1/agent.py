from fastapi import APIRouter, Depends, Request

from app.agents.agent import BayerAgent
from app.api.deps import get_agent, get_settings
from app.core.limiter import limiter
from app.models.agent import AgentRequest, AgentResponse

router = APIRouter()


@router.post("/agent", response_model=AgentResponse)
@limiter.limit(lambda: get_settings().rate_limit_agent)
async def run_agent(
    request: Request,
    body: AgentRequest,
    agent: BayerAgent = Depends(get_agent),
) -> AgentResponse:
    result = await agent.run(query=body.query, thread_id=body.thread_id, request_id=request.state.request_id)
    return AgentResponse(answer=result.answer, tool_calls=result.tool_calls)
