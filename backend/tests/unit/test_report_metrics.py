"""Unit tests for backend/domain/report_metrics.py."""

from backend.domain.report_metrics import REPORT_METRICS, REPORT_METRIC_BY_KEY


def test_report_metric_keys_are_unique():
    keys = [metric.key for metric in REPORT_METRICS]
    assert len(keys) == len(set(keys))


def test_report_metric_payload_fields_are_unique():
    fields = []
    for metric in REPORT_METRICS:
        fields.extend([
            metric.monthly_field,
            metric.deltas_field,
            metric.machine_deltas_field,
        ])
    assert len(fields) == len(set(fields))


def test_new_heat_metrics_use_iv_chain():
    for key in ["iv_heat", "heat_prod"]:
        assert REPORT_METRIC_BY_KEY[key].chain_kind == "iv"


def test_new_heat_metrics_have_expected_columns_and_excel_prefixes():
    assert REPORT_METRIC_BY_KEY["iv_heat"].column == "IV_INCL_HEAT_COSTS"
    assert REPORT_METRIC_BY_KEY["iv_heat"].excel_prefix == "IV_Heat"
    assert REPORT_METRIC_BY_KEY["heat_prod"].column == "HEAT_PRODUCTION__GWH"
    assert REPORT_METRIC_BY_KEY["heat_prod"].excel_prefix == "Heat_Prod"


def test_heat_costs_is_not_a_report_metric():
    assert "heat_cost" not in REPORT_METRIC_BY_KEY
