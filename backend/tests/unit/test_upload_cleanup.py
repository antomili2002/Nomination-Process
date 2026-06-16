import os
import shutil
from pathlib import Path

from backend.core.config import settings
from backend.storage import temp_files


def test_cleanup_stale_uploads_deletes_only_expired_directories(monkeypatch):
    upload_dir = _fresh_dir("ttl")
    old_upload = upload_dir / "old-upload"
    fresh_upload = upload_dir / "fresh-upload"
    marker_file = upload_dir / "not-a-directory.txt"
    old_upload.mkdir()
    fresh_upload.mkdir()
    marker_file.write_text("keep", encoding="utf-8")

    now = 10_000.0
    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    monkeypatch.setattr(settings, "upload_ttl_seconds", 100)
    os.utime(old_upload, (now - 200, now - 200))
    os.utime(fresh_upload, (now - 50, now - 50))

    deleted = temp_files.cleanup_stale_uploads(now=now)

    assert deleted == 1
    assert not old_upload.exists()
    assert fresh_upload.exists()
    assert marker_file.exists()


def test_cleanup_stale_uploads_returns_zero_when_upload_dir_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", _base_dir() / "missing")

    assert temp_files.cleanup_stale_uploads(now=10_000.0) == 0


def test_cleanup_stale_uploads_ignores_delete_failures(monkeypatch):
    upload_dir = _fresh_dir("failure")
    old_upload = upload_dir / "old-upload"
    old_upload.mkdir()

    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    monkeypatch.setattr(settings, "upload_ttl_seconds", 100)
    os.utime(old_upload, (9_800.0, 9_800.0))

    def fail_delete(_path):
        raise OSError("locked")

    monkeypatch.setattr(temp_files.shutil, "rmtree", fail_delete)

    deleted = temp_files.cleanup_stale_uploads(now=10_000.0)

    assert deleted == 0
    assert old_upload.exists()


def _fresh_dir(name: str) -> Path:
    path = _base_dir() / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _base_dir() -> Path:
    return Path("backend/tmp/unit_upload_cleanup")
