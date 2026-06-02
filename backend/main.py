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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _cleanup_stale_uploads()
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
