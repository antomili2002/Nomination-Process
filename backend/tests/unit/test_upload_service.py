import io
import shutil
import threading
from pathlib import Path

import pandas as pd
import pytest
from fastapi import UploadFile

from backend.core.config import settings
from backend.core.exceptions import InvalidUploadError, InvalidWorkbookError, ScenarioExtractionError
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


def test_process_upload_extracts_scenarios_and_cleans_data_concurrently(monkeypatch):
    info_df = pd.DataFrame([["Info"]])
    raw_data_df = pd.DataFrame({"raw": [1]})
    scenarios_df = pd.DataFrame(
        [{"index": 0, "scenario_name": "Base", "scenario_id": 1}]
    )
    clean_data_df = pd.DataFrame({"MACHINE_NAME": ["MACHINE_A"]})
    extract_started = threading.Event()
    clean_started = threading.Event()

    monkeypatch.setattr(
        upload_service,
        "save_upload",
        lambda _file: ("upload-1", Path("backend/tmp/unit_upload_service/sample.xlsx")),
    )
    monkeypatch.setattr(
        upload_service,
        "read_workbook_sheets",
        lambda _path: (info_df, raw_data_df),
    )
    monkeypatch.setattr(upload_service, "save_workbook_data", lambda *_args: None)

    def extract_probe(_info_df):
        extract_started.set()
        if not clean_started.wait(timeout=1):
            raise AssertionError("clean_data did not start while scenarios were extracted")
        return scenarios_df

    def clean_probe(_raw_data_df):
        clean_started.set()
        if not extract_started.wait(timeout=1):
            raise AssertionError("extract_scenarios did not start while data was cleaned")
        return clean_data_df

    monkeypatch.setattr(upload_service, "extract_scenarios", extract_probe)
    monkeypatch.setattr(upload_service, "clean_data", clean_probe)

    result = upload_service.process_upload(_upload_file("sample.xlsx", b"unused"))

    assert result.scenarios[0].scenario_name == "Base"
    assert result.machines == ["MACHINE_A"]


def test_process_upload_propagates_scenario_extraction_errors(monkeypatch):
    monkeypatch.setattr(
        upload_service,
        "save_upload",
        lambda _file: ("upload-1", Path("backend/tmp/unit_upload_service/sample.xlsx")),
    )
    monkeypatch.setattr(
        upload_service,
        "read_workbook_sheets",
        lambda _path: (pd.DataFrame([["Info"]]), pd.DataFrame({"raw": [1]})),
    )
    monkeypatch.setattr(upload_service, "clean_data", lambda _df: pd.DataFrame())

    def fail_extract(_info_df):
        raise ScenarioExtractionError("bad scenarios")

    monkeypatch.setattr(upload_service, "extract_scenarios", fail_extract)

    with pytest.raises(ScenarioExtractionError, match="bad scenarios"):
        upload_service.process_upload(_upload_file("sample.xlsx", b"unused"))


def test_process_upload_propagates_cleaning_errors(monkeypatch):
    monkeypatch.setattr(
        upload_service,
        "save_upload",
        lambda _file: ("upload-1", Path("backend/tmp/unit_upload_service/sample.xlsx")),
    )
    monkeypatch.setattr(
        upload_service,
        "read_workbook_sheets",
        lambda _path: (pd.DataFrame([["Info"]]), pd.DataFrame({"raw": [1]})),
    )
    monkeypatch.setattr(
        upload_service,
        "extract_scenarios",
        lambda _df: pd.DataFrame(
            [{"index": 0, "scenario_name": "Base", "scenario_id": 1}]
        ),
    )

    def fail_clean(_raw_data_df):
        raise InvalidWorkbookError("bad data")

    monkeypatch.setattr(upload_service, "clean_data", fail_clean)

    with pytest.raises(InvalidWorkbookError, match="bad data"):
        upload_service.process_upload(_upload_file("sample.xlsx", b"unused"))


def _fresh_dir(name: str) -> Path:
    path = Path("backend/tmp/unit_upload_service") / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path
