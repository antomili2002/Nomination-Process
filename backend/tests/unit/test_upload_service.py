import io
import shutil
from pathlib import Path

import pytest
from fastapi import UploadFile

from backend.core.config import settings
from backend.core.exceptions import InvalidUploadError
from backend.services import upload_service
from backend.storage.processed_uploads import load_workbook_data


def _upload_file(name: str, content: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


def test_process_upload_returns_metadata_and_persists_processed_workbook(
    monkeypatch, sample_workbook_bytes
):
    upload_dir = _fresh_dir("upload-service-success")
    monkeypatch.setattr(settings, "upload_dir", upload_dir)

    result = upload_service.process_upload(
        _upload_file("sample.xlsx", sample_workbook_bytes)
    )

    assert result.file_name == "sample.xlsx"
    assert len(result.scenarios) == 6
    assert result.machines == ["MACHINE_A"]

    loaded = load_workbook_data(upload_dir / result.upload_id)
    assert loaded.clean_data_df["SCENARIO_NAME"].tolist()[0] == "Base_IV"
    assert loaded.scenarios_df["scenario_name"].tolist() == [
        "Base_IV",
        "Outage_IV",
        "Final_IV",
        "Base_EV",
        "Outage_EV",
        "Final_EV",
    ]


def test_process_upload_rejects_non_xlsx(monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", _fresh_dir("upload-service-invalid"))

    with pytest.raises(InvalidUploadError, match="Only .xlsx"):
        upload_service.process_upload(_upload_file("bad.csv", b"a,b"))


def _fresh_dir(name: str) -> Path:
    path = Path("backend/tmp/unit_upload_service") / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path
