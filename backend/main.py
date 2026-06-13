import asyncio
import logging
import shutil
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_download import router as download_router
from backend.api.routes_reports import router as reports_router
from backend.api.routes_upload import router as upload_router
from backend.core.config import settings

_UPLOAD_TTL_SECONDS = 4 * 3600  # keep uploads for 4 hours
_LOGGER = logging.getLogger(__name__)


def _cleanup_stale_uploads() -> None:
    """Delete upload directories that are older than the TTL.

    Called once at application startup.  This is a best-effort sweep — errors
    for individual directories are ignored so a single bad entry cannot block
    the server from starting.
    """
    upload_dir = settings.upload_dir
    if not upload_dir.exists():
        return
    cutoff = time.time() - _UPLOAD_TTL_SECONDS
    for entry in upload_dir.iterdir():
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            pass


async def _cleanup_stale_uploads_in_background() -> None:
    await asyncio.to_thread(_cleanup_stale_uploads)


def _log_background_cleanup_result(task: asyncio.Task[None]) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        _LOGGER.exception("Upload cleanup failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cleanup_task = asyncio.create_task(_cleanup_stale_uploads_in_background())
    cleanup_task.add_done_callback(_log_background_cleanup_result)
    yield


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
