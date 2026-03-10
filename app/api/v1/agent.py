import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.agent import BayerAgent
from app.api.deps import get_agent, get_db, get_settings
from app.core.limiter import limiter
from app.db.models import QueryLog
from app.models.agent import AgentRequest, AgentResponse

router = APIRouter()


@router.post("/agent", response_model=AgentResponse)
@limiter.limit(lambda: get_settings().rate_limit_agent)
async def run_agent(
    request: Request,
    body: AgentRequest,
    agent: BayerAgent = Depends(get_agent),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    start = time.monotonic()
    result = await agent.run(
        query=body.query, thread_id=body.thread_id, request_id=request.state.request_id
    )
    latency_ms = (time.monotonic() - start) * 1000

    db.add(
        QueryLog(
            request_id=request.state.request_id,
            endpoint="/agent",
            input_text=body.query,
            response_text=result.answer,
            citation_count=len(result.citations),
            latency_ms=round(latency_ms, 2),
        )
    )
    await db.commit()

    return AgentResponse(
        answer=result.answer, tool_calls=result.tool_calls, citations=result.citations
    )
