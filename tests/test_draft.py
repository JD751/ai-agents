from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_draft_service
from app.main import app
from app.services.draft_service import DraftResult


@pytest.fixture
def client():
    mock_service = MagicMock()
    mock_service.draft.return_value = DraftResult(
        draft=(
            "Headline: Aspirin — Trusted Relief\n"
            "Body: Clinically proven to relieve mild to moderate pain. "
            "Backed by decades of research.\n"
            "CTA: Ask your pharmacist today."
        ),
        citations=["Angeliq_CMI.pdf"],
    )
    app.dependency_overrides[get_draft_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_draft_returns_200(client):
    resp = client.post("/api/v1/draft", json={"brief": "pain relief tablet for adults"})
    assert resp.status_code == 200


def test_draft_returns_non_empty_content(client):
    resp = client.post("/api/v1/draft", json={"brief": "pain relief tablet for adults"})
    data = resp.json()
    assert data["draft"], "draft must be a non-empty string"
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) > 0


def test_draft_calls_service_with_brief(client):
    brief = "allergy relief for seasonal sufferers"
    client.post("/api/v1/draft", json={"brief": brief})
    mock_service = app.dependency_overrides[get_draft_service]()
    mock_service.draft.assert_called_once_with(brief)
