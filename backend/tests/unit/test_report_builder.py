"""Unit tests for backend/processing/report_builder.py."""

import pytest

from backend.domain.report_metrics import REPORT_METRIC_BY_KEY
from backend.processing.chain_builder import build_delta_pairs
from backend.processing.cleaning import clean_data
from backend.processing.report_builder import build_metric_preview, build_metric_report

INDEX_TO_NAME = {
    0: "Base_IV",
    1: "Outage_IV",
    2: "Final_IV",
    3: "Base_EV",
    4: "Outage_EV",
    5: "Final_EV",
}


@pytest.fixture(scope="module")
def clean_df(data_df):
    return clean_data(data_df)


def test_build_metric_report_returns_all_payload_fields(clean_df):
    metric = REPORT_METRIC_BY_KEY["heat_prod"]
    pairs = build_delta_pairs([0, 2], INDEX_TO_NAME)

    result = build_metric_report(
        data_df=clean_df,
        chain_indices=[0, 2],
        pairs=pairs,
        metric=metric,
        index_to_name=INDEX_TO_NAME,
        selected_machines=None,
    )

    assert set(result) == {
        "heat_prod_monthly",
        "heat_prod_deltas",
    }


def test_build_metric_report_uses_metric_column_for_yearly_delta(clean_df):
    metric = REPORT_METRIC_BY_KEY["heat_prod"]
    pairs = build_delta_pairs([0, 2], INDEX_TO_NAME)

    result = build_metric_report(
        data_df=clean_df,
        chain_indices=[0, 2],
        pairs=pairs,
        metric=metric,
        index_to_name=INDEX_TO_NAME,
        selected_machines=None,
    )

    delta = result["heat_prod_deltas"][0]
    assert delta["left_total"] == pytest.approx(40.0)
    assert delta["right_total"] == pytest.approx(72.0)
    assert delta["delta_total"] == pytest.approx(32.0)


def test_build_metric_report_applies_machine_filter(clean_df):
    metric = REPORT_METRIC_BY_KEY["heat_prod"]
    pairs = build_delta_pairs([0, 2], INDEX_TO_NAME)

    result = build_metric_report(
        data_df=clean_df,
        chain_indices=[0, 2],
        pairs=pairs,
        metric=metric,
        index_to_name=INDEX_TO_NAME,
        selected_machines=["DOES_NOT_EXIST"],
    )

    delta = result["heat_prod_deltas"][0]
    assert delta["delta_total"] == pytest.approx(0.0)


def test_build_metric_preview_returns_monthly_deltas_for_dashboard(clean_df):
    metric = REPORT_METRIC_BY_KEY["heat_prod"]
    pairs = build_delta_pairs([0, 2], INDEX_TO_NAME)

    result = build_metric_preview(
        data_df=clean_df,
        chain_indices=[0, 2],
        pairs=pairs,
        metric=metric,
        index_to_name=INDEX_TO_NAME,
        selected_machines=None,
    )

    rows = result["heat_prod_deltas"][0]["rows"]
    assert rows[0]["values"] == [8.0, 8.0]
    assert rows[1]["values"] == [8.0, 8.0]
