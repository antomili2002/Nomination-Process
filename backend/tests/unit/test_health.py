import asyncio

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend import main
from backend.main import app


def test_healthz_returns_ok_status():
    client = TestClient(app)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_startup_starts_periodic_upload_cleanup_without_blocking(monkeypatch):
    cleanup_started = asyncio.Event()
    cleanup_calls: list[int] = []

    async def fake_cleanup() -> None:
        cleanup_calls.append(len(cleanup_calls))
        cleanup_started.set()

    monkeypatch.setattr(main, "_run_upload_cleanup_once", fake_cleanup)
    monkeypatch.setattr(settings, "upload_cleanup_interval_seconds", 3600)

    async def run_lifespan() -> None:
        async with main.lifespan(app):
            assert cleanup_calls == []
            await asyncio.wait_for(cleanup_started.wait(), timeout=1)
            assert cleanup_calls == [0]

    asyncio.run(run_lifespan())


def test_periodic_upload_cleanup_repeats_until_cancelled(monkeypatch):
    cleanup_calls: list[int] = []

    async def fake_cleanup() -> None:
        cleanup_calls.append(len(cleanup_calls))

    async def fake_sleep(_seconds: float) -> None:
        if len(cleanup_calls) >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(main, "_run_upload_cleanup_once", fake_cleanup)
    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(settings, "upload_cleanup_interval_seconds", 1)

    async def run_cleanup() -> None:
        try:
            await main._periodic_upload_cleanup()
        except asyncio.CancelledError:
            pass

    asyncio.run(run_cleanup())

    assert cleanup_calls == [0, 1]
