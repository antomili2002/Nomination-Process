import shutil
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from backend.core.config import settings
from backend.core.exceptions import InvalidUploadError


def save_upload(file: UploadFile) -> tuple[str, Path]:
    """Stream *file* to disk; return ``(upload_id, workbook_path)``."""
    _validate_extension(file.filename or "")

    upload_id = str(uuid.uuid4())
    dest_dir = settings.upload_dir / upload_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / (file.filename or "upload.xlsx")

    bytes_written = 0
    with dest_path.open("wb") as fh:
        while chunk := file.file.read(1024 * 256):  # 256 KB chunks
            bytes_written += len(chunk)
            if bytes_written > settings.max_upload_bytes:
                dest_path.unlink(missing_ok=True)
                raise InvalidUploadError(
                    f"File exceeds the maximum allowed size of "
                    f"{settings.max_upload_bytes // (1024 * 1024)} MB."
                )
            fh.write(chunk)

    return upload_id, dest_path


def get_upload_path(upload_id: str) -> Path:
    """Return the workbook path for a previously saved *upload_id*."""
    upload_dir = settings.upload_dir / upload_id
    files = list(upload_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No workbook found for upload_id={upload_id!r}")
    return files[0]


def save_report(report_id: str, data: bytes, filename: str) -> Path:
    """Persist a generated report and return its path."""
    report_dir = settings.report_dir / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / filename
    path.write_bytes(data)
    return path


def get_report_path(report_id: str) -> Path:
    """Return the path of the first Excel file in *report_id*'s directory."""
    report_dir = settings.report_dir / report_id
    files = list(report_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No report found for report_id={report_id!r}")
    return files[0]


def cleanup_stale_uploads(now: float | None = None) -> int:
    """Delete upload directories older than the configured TTL.

    Returns the number of directories deleted. Failures for individual
    directories are ignored so cleanup cannot break request handling.
    """
    upload_dir = settings.upload_dir
    if not upload_dir.exists():
        return 0

    cutoff = (time.time() if now is None else now) - settings.upload_ttl_seconds
    deleted = 0
    for entry in upload_dir.iterdir():
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry)
                deleted += 1
        except OSError:
            pass
    return deleted


# internal 
def _validate_extension(filename: str) -> None:
    if not filename.lower().endswith(".xlsx"):
        raise InvalidUploadError("Only .xlsx files are accepted.")
