import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_download import router as download_router
from backend.api.routes_reports import router as reports_router
from backend.api.routes_upload import router as upload_router
from backend.core.config import settings
from backend.storage.temp_files import cleanup_stale_uploads

_LOGGER = logging.getLogger(__name__)


async def _run_upload_cleanup_once() -> None:
    deleted = await asyncio.to_thread(cleanup_stale_uploads)
    if deleted:
        _LOGGER.info("Deleted %s stale upload directories", deleted)


async def _periodic_upload_cleanup() -> None:
    while True:
        try:
            await _run_upload_cleanup_once()
        except Exception:
            _LOGGER.exception("Upload cleanup failed")
        await asyncio.sleep(settings.upload_cleanup_interval_seconds)


def _log_background_cleanup_result(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        _LOGGER.exception("Upload cleanup failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_task = asyncio.create_task(_periodic_upload_cleanup())
    cleanup_task.add_done_callback(_log_background_cleanup_result)
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(title="Scenario Delta Report API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(reports_router)
app.include_router(download_router)


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
