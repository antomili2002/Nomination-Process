"""Unit tests for backend/domain/report_metrics.py."""

import pandas as pd

from backend.domain.report_metrics import REPORT_METRICS, REPORT_METRIC_BY_KEY, available_metrics


def test_report_metric_keys_are_unique():
    keys = [metric.key for metric in REPORT_METRICS]
    assert len(keys) == len(set(keys))


def test_new_heat_metrics_use_iv_chain():
    for key in ["iv_heat", "heat_prod"]:
        assert REPORT_METRIC_BY_KEY[key].chain_kind == "iv"


def test_new_heat_metrics_have_expected_columns_and_excel_prefixes():
    assert REPORT_METRIC_BY_KEY["iv_heat"].column == "IV_INCL_HEAT_COSTS"
    assert REPORT_METRIC_BY_KEY["iv_heat"].excel_prefix == "IV_Heat"
    assert REPORT_METRIC_BY_KEY["heat_prod"].column == "HEAT_PRODUCTION__GWH"
    assert REPORT_METRIC_BY_KEY["heat_prod"].excel_prefix == "Heat_Prod"


def test_available_metrics_returns_only_curated_metrics_with_matching_columns():
    df = pd.DataFrame({
        "SCENARIO_NAME": ["Base"],
        "EXTRINSIC_VALUE": [1.0],
        "INTRINSIC_VALUE__CUR": [2.0],
    })
    result = available_metrics(df)
    assert [m.key for m in result] == ["ev", "iv"]


def test_available_metrics_returns_all_curated_when_all_columns_present():
    df = pd.DataFrame({m.column: [1.0] for m in REPORT_METRICS} | {"SCENARIO_NAME": ["Base"]})
    result = available_metrics(df)
    assert set(m.key for m in result) == set(m.key for m in REPORT_METRICS)


def test_available_metrics_returns_empty_for_no_matching_columns():
    df = pd.DataFrame({"SCENARIO_NAME": ["Base"], "YEAR": [2026]})
    assert available_metrics(df) == ()


def test_available_metrics_discovers_dynamic_numeric_columns():
    df = pd.DataFrame({
        "SCENARIO_NAME": ["Base"],
        "YEAR": [2026],
        "EXTRINSIC_VALUE": [1.0],
        "TOTAL_VALUE__CUR": [42.0],
    })
    result = available_metrics(df)
    assert [m.key for m in result] == ["ev", "TOTAL_VALUE__CUR"]
    dynamic = result[1]
    assert dynamic.column == "TOTAL_VALUE__CUR"
    assert dynamic.label == "Total Value (CUR)"
    assert dynamic.chain_kind == "iv"
    assert dynamic.output_type == "IV"
    assert dynamic.excel_prefix == "TOTAL_VALUE__CUR"[:20]


def test_available_metrics_ignores_dimension_and_non_numeric_columns():
    df = pd.DataFrame({
        "SCENARIO_NAME": ["Base"],
        "YEAR": [2026],
        "MONTH": [5],
        "TARIFF": ["peak"],
        "PLANT_NAME": ["RATS"],
        "EXTRINSIC_VALUE": [1.0],
    })
    result = available_metrics(df)
    assert [m.key for m in result] == ["ev"]


def test_only_core_value_metrics_are_selected_by_default():
    defaults = {m.key: m.default_selected for m in REPORT_METRICS}
    assert defaults == {
        "ev": True,
        "iv": True,
        "pp": True,
        "iv_heat": False,
        "heat_prod": False,
    }


def test_curated_metrics_share_core_value_category():
    for metric in REPORT_METRICS:
        assert metric.category == "Core Value Metrics"


def test_dynamic_metrics_are_not_selected_by_default():
    df = pd.DataFrame({"SCENARIO_NAME": ["Base"], "TOTAL_VALUE__CUR": [1.0]})
    result = available_metrics(df)
    assert result[0].default_selected is False


def test_dynamic_metrics_are_categorized_by_keyword():
    df = pd.DataFrame({
        "SCENARIO_NAME": ["Base"],
        "RUNNING_HOURS__H": [1.0],
        "STARTS": [1.0],
        "FUEL_COST_TOT__CUR": [1.0],
        "CO2_POS_TOT__TCO2": [1.0],
        "WATER_VOLUMES_MM3": [1.0],
        "INCOME_FCRN": [1.0],
        "POWER_PRICE__CUR_PER_MWH": [1.0],
        "TAX_COST__CUR": [1.0],
        "FILLER_COLUMN": [1.0],
    })
    result = available_metrics(df)
    categories = {m.key: m.category for m in result}
    assert categories["RUNNING_HOURS__H"] == "Running Regime"
    assert categories["STARTS"] == "Running Regime"
    assert categories["FUEL_COST_TOT__CUR"] == "Fuel"
    assert categories["CO2_POS_TOT__TCO2"] == "Emissions (CO2 / SO2 / NOx)"
    assert categories["WATER_VOLUMES_MM3"] == "Water"
    assert categories["INCOME_FCRN"] == "Ancillary Services (FCR)"
    assert categories["POWER_PRICE__CUR_PER_MWH"] == "Pricing"
    assert categories["TAX_COST__CUR"] == "Costs"
    assert categories["FILLER_COLUMN"] == "Other Metrics"


def test_heat_costs_is_not_a_report_metric():
    assert "heat_cost" not in REPORT_METRIC_BY_KEY
