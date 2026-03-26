# ─── Stage 1: Builder ────────────────────────────────────────────────────────
# Use Poetry only in this stage to export a clean requirements.txt.
# Poetry itself will NOT be present in the final image.
FROM python:3.12-slim AS builder

# Install Poetry and the export plugin (required in Poetry 2.x)
RUN pip install --no-cache-dir poetry==2.1.1 poetry-plugin-export

WORKDIR /build

# Copy dependency files first to leverage Docker layer caching.
# Subsequent builds skip this layer if pyproject.toml/poetry.lock are unchanged.
COPY pyproject.toml poetry.lock ./

# Export production-only dependencies to requirements.txt.
# --without dev excludes pytest, black, mypy, etc.
# --no-interaction / --no-ansi keep output clean in CI.
RUN poetry export \
    --without dev \
    --no-interaction \
    --no-ansi \
    --format requirements.txt \
    --output requirements.txt


# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
# Fresh slim base — no Poetry, no build tools, no dev packages.
FROM python:3.12-slim AS runtime

# Create a non-root user and group.
# Running as root inside a container is a security risk — AKS will also
# enforce this via Pod Security Standards.
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

WORKDIR /app

# Install production dependencies from the exported requirements.txt.
# --no-cache-dir keeps the image layer small.
COPY --from=builder /build/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
# chroma_db/ and documents/ are intentionally excluded — documents live in Azure Blob Storage.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create chroma persistence directory and transfer ownership to non-root user.
RUN mkdir -p /chroma_db && \
    chown -R appuser:appgroup /app /chroma_db && \
    chmod -R 755 /app/alembic

# Switch to non-root user for all subsequent commands and at runtime.
USER appuser

# Expose the port uvicorn will listen on.
EXPOSE 8000

# Run uvicorn with a single worker by default.
# In production (AKS), horizontal scaling is handled at the pod level,
# so we keep one worker per container for predictable resource usage.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
