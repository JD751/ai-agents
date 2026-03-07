from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

from app.agents.agent import BayerAgent
from app.api.deps import get_agent, get_settings
from app.core.limiter import limiter
from app.models.agent import AgentRequest

router = APIRouter()


@router.post("/agent/stream")
@limiter.limit(lambda: get_settings().rate_limit_agent)
async def stream_agent(
    request: Request,
    body: AgentRequest,
    agent: BayerAgent = Depends(get_agent),
) -> EventSourceResponse:
    config = {
        "configurable": {"thread_id": body.thread_id},
        "tags": ["bayer-agent"],
        "metadata": {
            "thread_id": body.thread_id,
            "request_id": request.state.request_id,
        },
    }

    async def event_generator():
        async for event in agent._graph.astream_events(
            {"messages": [HumanMessage(content=body.query)]},
            config=config,
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    yield {"event": "token", "data": chunk.content}

            elif kind == "on_tool_start":
                yield {"event": "tool_start", "data": event.get("name", "")}

            elif kind == "on_tool_end":
                yield {"event": "tool_end", "data": event.get("name", "")}

        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
