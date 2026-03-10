from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health():
    """Liveness probe — fast, no I/O. Kubernetes uses this to know the process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(request: Request):
    """Readiness probe — checks downstream dependencies before accepting traffic."""
    checks: dict[str, str] = {}
    status = "ready"

    # Check vector store is reachable
    try:
        rag = getattr(request.app.state, "rag_service", None)
        if rag is None:
            raise RuntimeError("RAG service not initialised")
        rag.vector_store.get()  # lightweight Chroma metadata fetch
        checks["vector_store"] = "ok"
    except Exception as exc:
        checks["vector_store"] = f"error: {exc}"
        status = "degraded"

    # Check agent is initialised
    agent = getattr(request.app.state, "agent", None)
    checks["agent"] = "ok" if agent is not None else "not initialised"
    if agent is None:
        status = "degraded"

    return {"status": status, "checks": checks}
