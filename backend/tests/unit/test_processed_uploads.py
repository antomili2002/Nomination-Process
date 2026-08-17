import shutil
from pathlib import Path

import pandas as pd
import pytest

from backend.domain.workbook import WorkbookData
from backend.storage import processed_uploads


def test_save_and_load_workbook_data_round_trips_frames_and_metadata():
    upload_dir = _fresh_dir("processed-upload-roundtrip")
    info_df = pd.DataFrame([["Scenario Name", "Scenario ID"], ["Base", 1]])
    raw_data_df = pd.DataFrame({"SCENARIO_NAME": ["Base"], "VALUE": [10]})
    clean_data_df = pd.DataFrame({"SCENARIO_NAME": ["Base"], "VALUE": [10.0]})
    scenarios = pd.DataFrame(
        [{"index": 0, "scenario_name": "Base", "scenario_id": 1}]
    )
    machines = ["MACHINE_A", "MACHINE_B"]
    portfolio_country = "NL"

    processed_uploads.save_workbook_data(
        upload_dir,
        WorkbookData(
            info_df=info_df,
            raw_data_df=raw_data_df,
            clean_data_df=clean_data_df,
            scenarios_df=scenarios,
            machines=machines,
            portfolio_country=portfolio_country,
        ),
    )

    loaded = processed_uploads.load_workbook_data(upload_dir)

    pd.testing.assert_frame_equal(loaded.info_df, info_df)
    pd.testing.assert_frame_equal(loaded.raw_data_df, raw_data_df)
    pd.testing.assert_frame_equal(loaded.clean_data_df, clean_data_df)
    pd.testing.assert_frame_equal(loaded.scenarios_df, scenarios)
    assert loaded.machines == machines
    assert loaded.portfolio_country == portfolio_country


def test_load_workbook_data_raises_file_not_found_for_missing_artifacts():
    with pytest.raises(FileNotFoundError):
        processed_uploads.load_workbook_data(_base_dir() / "missing")


def _fresh_dir(name: str) -> Path:
    path = _base_dir() / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _base_dir() -> Path:
    return Path("backend/tmp/unit_processed_uploads")
