"""IV and EV scenario chains are each optional, but at least one is required."""
import pytest

from backend.core.exceptions import InvalidChainError
from backend.domain.workbook import WorkbookData
from backend.processing.chain_builder import NO_SCENARIOS_SELECTED_MESSAGE
from backend.processing.cleaning import clean_data
from backend.processing.readers import read_workbook_sheets
from backend.processing.scenario_extraction import extract_scenarios
from backend.excel import report_writer
from backend.services import report_service

_IV_CHAIN = [0, 2]
_EV_CHAIN = [3, 5]
_IV_METRIC_KEYS = {"iv", "pp", "iv_heat", "heat_prod"}


@pytest.fixture(params=["UK", "NL"])
def workbook(request, sample_workbook_path) -> WorkbookData:
    info_df, raw_data_df = read_workbook_sheets(sample_workbook_path)
    return WorkbookData(
        info_df=info_df,
        raw_data_df=raw_data_df,
        clean_data_df=clean_data(raw_data_df),
        scenarios_df=extract_scenarios(info_df),
        machines=["MACHINE_A"],
        portfolio_country=request.param,
    )


def _generate(workbook: WorkbookData, iv_chain, ev_chain, selected_metrics=None) -> dict:
    return report_service.generate_report_from_workbook(
        workbook, "upload-1", iv_chain, ev_chain,
        selected_machines=None, selected_metrics=selected_metrics,
    )


def _output_types(result: dict) -> set[str]:
    if result["layout"] == "non_uk":
        return {s["output_type"] for s in result["non_uk_sections"]}
    return {m["output_type"] for m in result["metrics"]}


# 1. No IV scenarios selected (EV only)

def test_ev_only_generates_ev_metrics(workbook):
    result = _generate(workbook, [], _EV_CHAIN)
    assert _output_types(result) == {"EV"}


def test_ev_only_values_match_full_report(workbook):
    ev_only = _generate(workbook, [], _EV_CHAIN, ["ev"])
    full = _generate(workbook, _IV_CHAIN, _EV_CHAIN, ["ev"])
    assert ev_only["metrics"] == full["metrics"]
    assert ev_only["non_uk_sections"] == full["non_uk_sections"]


def test_ev_only_with_only_iv_metrics_selected_raises(workbook):
    with pytest.raises(InvalidChainError, match="IV scenario chain"):
        _generate(workbook, [], _EV_CHAIN, ["iv", "pp"])


def test_ev_only_report_can_be_written_to_excel(workbook):
    result = _generate(workbook, [], _EV_CHAIN)
    excel = report_writer.write_report(result, workbook.info_df, workbook.raw_data_df)
    assert excel.startswith(b"PK")


# 2. No EV scenarios selected (IV only)

def test_iv_only_generates_iv_metrics(workbook):
    result = _generate(workbook, _IV_CHAIN, [])
    assert _output_types(result) == {"IV"}
    if result["layout"] != "non_uk":
        assert {m["key"] for m in result["metrics"]} == _IV_METRIC_KEYS


def test_iv_only_values_match_full_report(workbook):
    metrics = ["iv", "pp"]
    iv_only = _generate(workbook, _IV_CHAIN, [], metrics)
    full = _generate(workbook, _IV_CHAIN, _EV_CHAIN, metrics)
    assert iv_only["metrics"] == full["metrics"]
    assert iv_only["non_uk_sections"] == full["non_uk_sections"]


def test_iv_only_with_only_ev_metric_selected_raises(workbook):
    with pytest.raises(InvalidChainError, match="EV scenario chain"):
        _generate(workbook, _IV_CHAIN, [], ["ev"])


def test_iv_only_report_can_be_written_to_excel(workbook):
    result = _generate(workbook, _IV_CHAIN, [])
    excel = report_writer.write_report(result, workbook.info_df, workbook.raw_data_df)
    assert excel.startswith(b"PK")


# 3. No scenarios selected at all

def test_no_scenarios_selected_raises_with_guidance(workbook):
    with pytest.raises(InvalidChainError) as exc_info:
        _generate(workbook, [], [])
    assert str(exc_info.value) == NO_SCENARIOS_SELECTED_MESSAGE


# Live data preview

def test_preview_ev_only_returns_empty_iv_tables(workbook):
    result = report_service.preview_data_from_workbook(workbook, [], _EV_CHAIN, None)
    assert len(result["ev_monthly"]) == 2
    assert result["iv_monthly"] == []
    assert result["iv_deltas"] == []
    assert result["pp_monthly"] == []


def test_preview_iv_only_returns_empty_ev_tables(workbook):
    result = report_service.preview_data_from_workbook(workbook, _IV_CHAIN, [], None)
    assert len(result["iv_monthly"]) == 2
    assert result["ev_monthly"] == []
    assert result["ev_deltas"] == []


def test_preview_no_scenarios_raises(workbook):
    with pytest.raises(InvalidChainError, match="at least one"):
        report_service.preview_data_from_workbook(workbook, [], [], None)
