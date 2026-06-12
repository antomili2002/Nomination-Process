from fastapi.testclient import TestClient

from backend.main import app


def test_healthz_returns_ok_status():
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
