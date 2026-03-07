Day 5 Plan: Production Hardening
Context
Days 1-4 produced a working FastAPI + LangGraph agent with RAG, draft generation, compliance review, ChromaDB vector store, and LangSmith tracing. The API has zero middleware, no rate limiting, no timeouts, no retry logic, and no queue architecture. Day 5 transforms it from a functional prototype into a production-ready service.

Goals
Request timeout handling
Rate limiting (per-IP, per-endpoint)
Queue consumer and worker architecture
Retry logic for LLM calls
Structured logging for prompts and outputs
Basic response validation
SSE streaming for frontend communication
API robustness (exception handling, request IDs, enhanced health check)
Implementation Sequence
Step 0 — Create day5.md in project root
Write the full Day 5 plan to /home/agent_x/projects/bayer-ai/day5.md as a reference document for the implementation.

Step 1 — Add dependencies to pyproject.toml
Add to production deps:


slowapi = "^0.1"
tenacity = "^8.5"
sse-starlette = "^2.1"
Run poetry add slowapi tenacity sse-starlette.

Step 2 — app/config/settings.py
Add new fields:


request_timeout_seconds: float = 30.0
queue_max_size: int = 100
queue_workers: int = 2
rate_limit_default: str = "60/minute"
Step 3 — app/core/middleware.py (NEW)
Three components in one file:

RequestIDMiddleware — runs first on every request, sets request.state.request_id from incoming X-Request-ID header or generates a UUID. Echoes it back in response headers.

TimeoutMiddleware — wraps call_next with asyncio.wait_for(call_next(request), timeout=settings.request_timeout_seconds). Returns 504 JSON on timeout. Note: cancels the coroutine but does not kill background threads — this is correct and honest behavior.

global_exception_handler — catches unhandled Exception, logs with request_id and path, returns structured {"detail": "Internal server error", "request_id": "..."} as 500 JSON.

Registration order in app/main.py (LIFO — last registered = first executed):


app.add_middleware(TimeoutMiddleware, timeout=settings.request_timeout_seconds)
app.add_middleware(RequestIDMiddleware)   # runs first
app.add_exception_handler(Exception, global_exception_handler)
Step 4 — app/core/limiter.py (NEW)

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
Register in app/main.py:


from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
Add request: Request parameter and @limiter.limit(...) decorator to each route:

/agent — "10/minute" (multiple LLM calls per request)
/ask — "30/minute"
/draft — "20/minute"
/review — "20/minute"
/ingest — "5/minute" (disk + vector DB I/O)


Step 5 — app/core/retry.py (NEW)

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai

llm_retry = retry(
    retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
Wrap chain.invoke calls in each service with a private @llm_retry helper function:


@llm_retry
def _invoke(chain, inputs):
    return chain.invoke(inputs)
Apply in: rag_service.py, draft_service.py, review_service.py.
For agents/agent.py, use tenacity's AsyncRetrying context manager around ainvoke.

Step 6 — app/core/log_context.py (NEW)

def log_llm_event(logger, *, event, request_id, prompt_preview, response_preview,
                  latency_ms, model, token_usage=None, citations=None, tools_used=None):
    logger.info(event, extra={
        "request_id": request_id,
        "prompt_preview": prompt_preview[:200],
        "response_preview": response_preview[:200],
        "latency_ms": round(latency_ms, 2),
        "model": model,
        "token_usage": token_usage,
        "citations": citations,
        "tools_used": tools_used,
    })
Wire into service methods by:

Adding request_id: str = "unknown" kwarg to each service method signature
Wrapping chain.invoke with time.perf_counter() before/after for latency_ms
Calling log_llm_event(...) after each LLM call
Route handlers pass request.state.request_id into service calls.

Files to modify: rag_service.py, draft_service.py, review_service.py, agents/agent.py.

Step 7 — app/core/validators.py (NEW)
Post-LLM content validators called in route handlers after service returns:


def validate_ask_response(answer: str) -> None:
    if len(answer.strip()) < 10: raise ResponseValidationError("Answer too short")
    if len(answer) > 5000: raise ResponseValidationError("Answer too long")

def validate_draft_response(draft: str) -> None:
    if len(draft.strip()) < 20: raise ResponseValidationError("Draft too short")

def validate_review_response(notes: list[str]) -> None:
    if not notes: raise ResponseValidationError("Review returned no notes")
ResponseValidationError maps to HTTP 422 in the global exception handler.

Step 8 — app/core/queue.py (NEW)
asyncio.Queue-based background task queue:


class TaskQueue:
    def __init__(self, max_size, num_workers)
    async def start() -> None       # create worker tasks
    async def stop() -> None        # cancel workers gracefully
    async def enqueue(task_id, fn, *args, **kwargs) -> None
    def get_result(task_id) -> dict | None  # {"status": "pending|complete|error", ...}
Workers are asyncio.Task coroutines that pull from the queue, await the function, and store results in an in-memory dict keyed by task_id.

Wire into app/main.py lifespan:


app.state.task_queue = TaskQueue(max_size=settings.queue_max_size, num_workers=settings.queue_workers)
await app.state.task_queue.start()
yield
await asyncio.wait_for(app.state.task_queue._queue.join(), timeout=10.0)
await app.state.task_queue.stop()
Add dependency to app/api/deps.py:


def get_task_queue(request: Request) -> TaskQueue:
    return request.app.state.task_queue
Step 9 — app/api/v1/jobs.py (NEW)
Two endpoints exposing the queue pattern:

POST /agent/async — enqueues agent.run(), returns {"job_id": "<uuid>"}
GET /agent/jobs/{job_id} — polls result dict, returns status + result when complete
Step 10 — app/api/v1/stream.py (NEW)
SSE streaming endpoint using sse-starlette and LangGraph's astream_events:


@router.post("/agent/stream")
async def stream_agent(request: Request, body: AgentRequest, agent: BayerAgent = Depends(get_agent)):
    async def event_generator():
        async for event in agent._graph.astream_events(..., version="v2"):
            if event["event"] == "on_chat_model_stream":
                yield {"event": "token", "data": chunk.content}
            elif event["event"] == "on_tool_start":
                yield {"event": "tool_start", "data": event["name"]}
            elif event["event"] == "on_tool_end":
                yield {"event": "tool_end", "data": event["name"]}
    return EventSourceResponse(event_generator())
Frontend connects via POST /api/v1/agent/stream, receives progressive token, tool_start, tool_end, done events. SSE is preferred over WebSockets because it's HTTP-based (works through proxies/load balancers), unidirectional (agent only pushes), and auto-reconnects in browsers.

Step 11 — app/api/v1/health.py
Add /health/ready deep readiness check alongside existing /health liveness:

Checks vector store is accessible
Checks agent is initialized on app.state
Reports queue depth if queue is running
Returns {"status": "ready"|"degraded", "checks": {...}}
Two-endpoint pattern: /health for k8s liveness (fast, no I/O), /health/ready for readiness probes.

Step 12 — Register new routers in app/api/v1/router.py

from app.api.v1 import stream, jobs
router.include_router(stream.router, tags=["streaming"])
router.include_router(jobs.router, tags=["jobs"])
