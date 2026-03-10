from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_ingest_service
from app.main import app
from app.services.ingest_service import IngestResult


@pytest.fixture
def client():
    mock_service = MagicMock()
    mock_service.ingest_async = AsyncMock(
        return_value=IngestResult(chunks_added=42, files_processed=3)
    )
    app.dependency_overrides[get_ingest_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_ingest_returns_200(client):
    resp = client.post("/api/v1/ingest")
    assert resp.status_code == 200


def test_ingest_returns_chunk_and_file_counts(client):
    resp = client.post("/api/v1/ingest")
    data = resp.json()
    assert data["chunks_added"] == 42
    assert data["files_processed"] == 3


def test_ingest_zero_chunks_when_no_documents(client):
    mock_service = app.dependency_overrides[get_ingest_service]()
    mock_service.ingest_async = AsyncMock(
        return_value=IngestResult(chunks_added=0, files_processed=0)
    )
    resp = client.post("/api/v1/ingest")
    data = resp.json()
    assert data["chunks_added"] == 0
    assert data["files_processed"] == 0
