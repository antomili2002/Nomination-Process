import io
import shutil
from pathlib import Path

from fastapi import UploadFile

from backend.core.config import settings
from backend.domain.workbook import WorkbookData
from backend.processing.cleaning import clean_data
from backend.processing.readers import read_workbook_sheets
from backend.processing.scenario_extraction import extract_scenarios
from backend.processing import report_builder
from backend.services import download_service, report_service, upload_service


_IV_CHAIN = [0, 2]
_EV_CHAIN = [3, 5]


def test_generate_report_uses_processed_upload_artifacts(
    monkeypatch, sample_workbook_bytes
):
    upload_dir = _fresh_dir("report-service-generate")
    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    uploaded = upload_service.process_upload(_upload_file(sample_workbook_bytes))

    def fail_if_excel_is_reopened(*_args, **_kwargs):
        raise AssertionError("report generation reopened the original workbook")

    def fail_if_data_is_recleaned(*_args, **_kwargs):
        raise AssertionError("report generation recleaned workbook data")

    monkeypatch.setattr(
        report_service,
        "read_workbook_sheets",
        fail_if_excel_is_reopened,
        raising=False,
    )
    monkeypatch.setattr(report_service, "clean_data", fail_if_data_is_recleaned, raising=False)

    result = report_service.generate_report(
        uploaded.upload_id, _IV_CHAIN, _EV_CHAIN, selected_machines=None
    )

    assert result["upload_id"] == uploaded.upload_id
    ev_metric = next(m for m in result["metrics"] if m["key"] == "ev")
    assert ev_metric["deltas"][0]["delta_total"] == 3200.0


def test_export_uses_processed_upload_artifacts(monkeypatch, sample_workbook_bytes):
    upload_dir = _fresh_dir("download-service-export")
    monkeypatch.setattr(settings, "upload_dir", upload_dir)
    uploaded = upload_service.process_upload(_upload_file(sample_workbook_bytes))

    def fail_if_excel_is_reopened(*_args, **_kwargs):
        raise AssertionError("export reopened the original workbook")

    monkeypatch.setattr(
        download_service,
        "read_workbook_sheets",
        fail_if_excel_is_reopened,
        raising=False,
    )
    monkeypatch.setattr(
        report_service,
        "read_workbook_sheets",
        fail_if_excel_is_reopened,
        raising=False,
    )

    excel_bytes, filename = download_service.create_excel_report(
        uploaded.upload_id, _IV_CHAIN, _EV_CHAIN, selected_machines=None
    )

    assert filename.startswith("scenario_report_")
    assert excel_bytes.startswith(b"PK")


def test_generate_report_reuses_monthly_aggregations(
    monkeypatch, sample_workbook_path
):
    info_df, raw_data_df = read_workbook_sheets(sample_workbook_path)
    workbook = WorkbookData(
        info_df=info_df,
        raw_data_df=raw_data_df,
        clean_data_df=clean_data(raw_data_df),
        scenarios_df=extract_scenarios(info_df),
        machines=["MACHINE_A"],
    )
    calls = []
    original = report_builder.aggregate_monthly

    def counting_aggregate(*args, **kwargs):
        calls.append((tuple(args[1]), args[2]))
        return original(*args, **kwargs)

    monkeypatch.setattr(report_builder, "aggregate_monthly", counting_aggregate)

    report_service.generate_report_from_workbook(
        workbook, "upload-1", _IV_CHAIN, _EV_CHAIN, selected_machines=None
    )

    assert len(calls) == len(set(calls))


def test_non_uk_report_groups_selected_metrics_by_iv_ev_category_and_period(
    sample_workbook_path,
):
    info_df, raw_data_df = read_workbook_sheets(sample_workbook_path)
    workbook = WorkbookData(
        info_df=info_df,
        raw_data_df=raw_data_df,
        clean_data_df=clean_data(raw_data_df),
        scenarios_df=extract_scenarios(info_df),
        machines=["MACHINE_A"],
        portfolio_country="NL",
    )

    result = report_service.generate_report_from_workbook(
        workbook,
        "upload-1",
        _IV_CHAIN,
        _EV_CHAIN,
        selected_machines=None,
        selected_metrics=["ev", "iv", "pp"],
    )

    assert result["layout"] == "non_uk"
    assert result["metrics"] == []
    sections = {(s["output_type"], s["period"]): s for s in result["non_uk_sections"]}
    assert set(sections) == {
        ("IV", "monthly"),
        ("IV", "yearly"),
        ("EV", "monthly"),
        ("EV", "yearly"),
    }

    iv_yearly = sections[("IV", "yearly")]
    assert iv_yearly["category"] == "Core Value Metrics"
    assert [column["label"] for column in iv_yearly["columns"]] == [
        "Base_IV",
        "Final_IV",
        "Final_IV - Base_IV",
    ]
    assert [row["metric_key"] for row in iv_yearly["rows"]] == ["iv", "pp"]
    assert iv_yearly["rows"][0] == {
        "metric_key": "iv",
        "metric_label": "Intrinsic Value",
        "year": 2026,
        "values": [4000.0, 7200.0, 3200.0],
    }
    assert "tariff" not in iv_yearly["rows"][0]
    assert all("%" not in column["label"] for column in iv_yearly["columns"])

    ev_yearly = sections[("EV", "yearly")]
    assert [row["metric_key"] for row in ev_yearly["rows"]] == ["ev"]

    iv_monthly = sections[("IV", "monthly")]
    assert iv_monthly["rows"][0] == {
        "metric_key": "iv",
        "metric_label": "Intrinsic Value",
        "year": 2026,
        "month": 5,
        "values": [2000.0, 3600.0, 1600.0],
    }


def _upload_file(content: bytes) -> UploadFile:
    return UploadFile(filename="sample.xlsx", file=io.BytesIO(content))


def _fresh_dir(name: str) -> Path:
    path = Path("backend/tmp/unit_report_service") / name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path
