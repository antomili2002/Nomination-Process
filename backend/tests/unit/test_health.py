import asyncio

from fastapi.testclient import TestClient

from backend import main
from backend.main import app


def test_healthz_returns_ok_status():
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_does_not_block_on_upload_cleanup(monkeypatch):
    cleanup_calls: list[str] = []

    def fake_cleanup() -> None:
        cleanup_calls.append("cleanup")

    monkeypatch.setattr(main, "_cleanup_stale_uploads", fake_cleanup)

    async def run_lifespan() -> None:
        async with main.lifespan(app):
            assert cleanup_calls == []
            await asyncio.sleep(0)
            assert cleanup_calls == ["cleanup"]

    asyncio.run(run_lifespan())
