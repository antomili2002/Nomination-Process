"""Unit tests for backend/processing/delta_output.py"""
import pytest

from backend.core.constants import (
    EV_COL,
    MONTH_COL,
    SCENARIO_NAME_COL,
    TARIFF_COL,
    YEAR_COL,
)
from backend.processing.cleaning import clean_data
from backend.processing.delta_output import compute_delta
from backend.processing.monthly_output import aggregate_monthly


@pytest.fixture(scope="module")
def clean_df(data_df):
    return clean_data(data_df)


@pytest.fixture(scope="module")
def base_monthly(clean_df):
    return aggregate_monthly(clean_df, ["Base_EV"], EV_COL)


@pytest.fixture(scope="module")
def outage_monthly(clean_df):
    return aggregate_monthly(clean_df, ["Outage_EV"], EV_COL)


@pytest.fixture(scope="module")
def final_monthly(clean_df):
    return aggregate_monthly(clean_df, ["Final_EV"], EV_COL)


# Fixture data values (per tariff, per month):
#   Base_EV = 500, Outage_EV = 700, Final_EV = 1300
#
# Expected deltas (right - left):
#   Step 1  Base_EV → Outage_EV  : 700  - 500  = 200
#   Step 2  Outage_EV → Final_EV : 1300 - 700  = 600
#   Cumul   Base_EV → Final_EV   : 1300 - 500  = 800
#
# Step 1 + Step 2 = 200 + 600 = 800 = Cumulative ✓


def test_step1_delta_value_is_200(base_monthly, outage_monthly):
    result = compute_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    assert all(result[EV_COL] == 200.0)


def test_step2_delta_value_is_600(outage_monthly, final_monthly):
    result = compute_delta(outage_monthly, final_monthly, EV_COL, "Outage_EV", "Final_EV")
    assert all(result[EV_COL] == 600.0)


def test_cumulative_delta_value_is_800(base_monthly, final_monthly):
    result = compute_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert all(result[EV_COL] == 800.0)


def test_step1_plus_step2_equals_cumulative(base_monthly, outage_monthly, final_monthly):
    step1 = compute_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    step2 = compute_delta(outage_monthly, final_monthly, EV_COL, "Outage_EV", "Final_EV")
    cumul = compute_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    # Deltas are additive because the chain is cumulative
    assert list((step1[EV_COL] + step2[EV_COL]).round(10)) == list(cumul[EV_COL].round(10))


def test_correct_columns_returned(base_monthly, outage_monthly):
    result = compute_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    assert set(result.columns) == {SCENARIO_NAME_COL, TARIFF_COL, YEAR_COL, MONTH_COL, EV_COL}


def test_scenario_name_encodes_pair(base_monthly, final_monthly):
    result = compute_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert all(result[SCENARIO_NAME_COL] == "Base_EV → Final_EV")


def test_tariff_dimension_preserved(base_monthly, outage_monthly):
    result = compute_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    assert TARIFF_COL in result.columns
    assert set(result[TARIFF_COL].unique()) == {"peak", "offpeak"}


def test_row_count_matches_input(base_monthly, outage_monthly):
    result = compute_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    # same (tariff, year, month) combinations as the inputs: 2 tariffs × 2 months = 4
    assert len(result) == len(base_monthly)


def test_missing_right_cells_treated_as_zero(base_monthly):
    import pandas as pd
    empty_right = pd.DataFrame(
        columns=[TARIFF_COL, YEAR_COL, MONTH_COL, EV_COL]
    )
    result = compute_delta(base_monthly, empty_right, EV_COL, "Base_EV", "Empty")
    # delta = 0 - 500 = -500 (right missing = 0)
    assert all(result[EV_COL] == -500.0)
