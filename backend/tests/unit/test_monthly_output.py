"""Unit tests for backend/processing/monthly_output.py"""
import pytest

from backend.core.constants import (
    EV_COL,
    IV_COL,
    MACHINE_NAME_COL,
    MONTH_COL,
    SCENARIO_NAME_COL,
    TARIFF_COL,
    YEAR_COL,
)
from backend.processing.cleaning import clean_data
from backend.processing.monthly_output import aggregate_monthly


@pytest.fixture(scope="module")
def clean_df(data_df):
    return clean_data(data_df)


# Fixture data recap:
#   6 scenarios × 1 machine × 2 tariffs (peak, offpeak) × 2 months (5, 6) = 24 rows
#   EV values per row: Base_EV=500, Outage_EV=700, Final_EV=1300
#   IV values per row: Base_IV=1000, Outage_IV=1200, Final_IV=1800
#
#   After aggregate_monthly (sum over machine, keep tariff):
#     Only 1 machine → per-(scenario, tariff, month) value is unchanged:
#     Base_EV peak = 500, Base_EV offpeak = 500, Final_EV = 1300 etc.


def test_only_requested_scenarios_are_returned(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV", "Final_EV"], EV_COL)
    assert set(result[SCENARIO_NAME_COL].unique()) == {"Base_EV", "Final_EV"}


def test_intermediate_scenario_excluded(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV", "Final_EV"], EV_COL)
    assert "Outage_EV" not in result[SCENARIO_NAME_COL].values


def test_tariff_is_preserved_as_dimension(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV"], EV_COL)
    assert TARIFF_COL in result.columns
    assert set(result[TARIFF_COL].unique()) == {"peak", "offpeak"}


def test_machine_column_not_in_output(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV"], EV_COL)
    assert MACHINE_NAME_COL not in result.columns


def test_values_not_summed_over_tariffs(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV"], EV_COL)
    # Single machine: each (tariff, month) cell = 500, not 1000
    assert all(result[EV_COL] == 500.0)


def test_row_count_per_scenario(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV", "Final_EV"], EV_COL)
    # 2 scenarios × 2 tariffs × 2 months = 8 rows
    assert len(result) == 8


def test_correct_columns_returned(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV"], EV_COL)
    assert set(result.columns) == {SCENARIO_NAME_COL, TARIFF_COL, YEAR_COL, MONTH_COL, EV_COL}


def test_result_sorted_by_group_keys(clean_df):
    result = aggregate_monthly(clean_df, ["Base_EV", "Final_EV"], EV_COL)
    months = result.loc[
        (result[SCENARIO_NAME_COL] == "Base_EV") & (result[TARIFF_COL] == "peak"),
        MONTH_COL,
    ].tolist()
    assert months == sorted(months)


def test_machine_filter_selects_correct_machine(clean_df):
    result = aggregate_monthly(
        clean_df, ["Base_EV"], EV_COL, selected_machines=["MACHINE_A"]
    )
    assert all(result[EV_COL] == 500.0)


def test_machine_filter_unknown_returns_empty(clean_df):
    result = aggregate_monthly(
        clean_df, ["Base_EV"], EV_COL, selected_machines=["DOES_NOT_EXIST"]
    )
    assert result.empty


def test_machine_filter_empty_list_returns_empty(clean_df):
    result = aggregate_monthly(
        clean_df, ["Base_EV", "Final_EV"], EV_COL, selected_machines=[]
    )
    assert result.empty


def test_machine_filter_none_includes_all(clean_df):
    # With 1 machine the sum equals the single machine's value
    result_all = aggregate_monthly(clean_df, ["Base_EV"], EV_COL, selected_machines=None)
    result_mach = aggregate_monthly(
        clean_df, ["Base_EV"], EV_COL, selected_machines=["MACHINE_A"]
    )
    assert list(result_all[EV_COL]) == list(result_mach[EV_COL])


def test_iv_metric_correct_value(clean_df):
    result = aggregate_monthly(clean_df, ["Base_IV"], IV_COL)
    # Single machine: each (tariff, month) row = 1000
    assert all(result[IV_COL] == 1000.0)
