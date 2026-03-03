from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "bayer-ai"
    assert body["status"] == "ok"
    assert body["version"] == "v1"

