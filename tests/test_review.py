from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_review_service
from app.main import app
from app.services.review_service import ReviewResult, _parse_response


# --- Unit tests for _parse_response (no mocking needed) ---

def test_parse_response_compliant():
    content = (
        "VERDICT: COMPLIANT\n"
        "NOTES:\n"
        "- Claim is supported by product monograph.\n"
        "- No prohibited language detected."
    )
    result = _parse_response(content)
    assert result.is_compliant is True
    assert len(result.notes) == 2
    assert "product monograph" in result.notes[0]


def test_parse_response_non_compliant():
    content = (
        "VERDICT: NON-COMPLIANT\n"
        "NOTES:\n"
        "- Claim 'cures all diseases' is not substantiated.\n"
        "- Superlative language is prohibited under section 4.2."
    )
    result = _parse_response(content)
    assert result.is_compliant is False
    assert len(result.notes) == 2


def test_parse_response_falls_back_to_raw_content_when_no_notes():
    content = "VERDICT: COMPLIANT\nNo specific notes."
    result = _parse_response(content)
    assert result.is_compliant is True
    assert result.notes == [content.strip()]


# --- Endpoint tests ---

@pytest.fixture
def client():
    mock_service = MagicMock()
    mock_service.review.return_value = ReviewResult(
        is_compliant=True,
        notes=["Claim is supported by the product monograph."],
    )
    app.dependency_overrides[get_review_service] = lambda: mock_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_review_returns_200(client):
    resp = client.post("/api/v1/review", json={"text": "Aspirin relieves headaches."})
    assert resp.status_code == 200


def test_review_returns_bool_and_notes(client):
    resp = client.post("/api/v1/review", json={"text": "Aspirin relieves headaches."})
    data = resp.json()
    assert isinstance(data["is_compliant"], bool)
    assert isinstance(data["notes"], list)
    assert len(data["notes"]) > 0


def test_review_non_compliant_response(client):
    mock_service = app.dependency_overrides[get_review_service]()
    mock_service.review.return_value = ReviewResult(
        is_compliant=False,
        notes=["Unsupported claim detected."],
    )
    resp = client.post("/api/v1/review", json={"text": "This product cures everything."})
    data = resp.json()
    assert data["is_compliant"] is False
    assert data["notes"] == ["Unsupported claim detected."]


def test_review_calls_service_with_text(client):
    text = "Aspirin is safe for daily use."
    client.post("/api/v1/review", json={"text": text})
    mock_service = app.dependency_overrides[get_review_service]()
    mock_service.review.assert_called_once_with(text)
