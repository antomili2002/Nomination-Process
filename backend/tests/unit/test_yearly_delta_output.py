"""Unit tests for backend/processing/yearly_delta_output.py

Fixture data recap (from conftest.py):
  Each scenario: 1 year (2026) × 2 tariffs × 2 months = 4 rows per scenario.
  EV values per row: Base_EV=500, Outage_EV=700, Final_EV=1300

  After aggregate_monthly the shape is (SCENARIO, TARIFF, YEAR, MONTH).
  compute_yearly_delta then sums over TARIFF and MONTH, so per-year totals are:

    Base_EV   → 500  × 4 =  2 000
    Outage_EV → 700  × 4 =  2 800
    Final_EV  → 1300 × 4 =  5 200

  Expected deltas (right − left):
    Base   → Outage : 2 800 −  2 000 =    800
    Outage → Final  : 5 200 −  2 800 =  2 400
    Base   → Final  : 5 200 −  2 000 =  3 200   (= 800 + 2400 ✓)
"""
import pytest

from backend.core.constants import EV_COL
from backend.processing.cleaning import clean_data
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.yearly_delta_output import compute_yearly_delta


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


# Return shape
def test_returns_expected_top_level_keys(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert set(result) == {"left_name", "right_name", "rows", "left_total", "right_total", "delta_total"}


def test_each_row_has_required_keys(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    for row in result["rows"]:
        assert set(row) == {"year", "left_value", "right_value", "delta"}


def test_names_are_preserved(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert result["left_name"] == "Base_EV"
    assert result["right_name"] == "Final_EV"


# Correct aggregation — Base → Final
def test_left_total_base_ev(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert result["left_total"] == pytest.approx(2000.0)


def test_right_total_final_ev(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert result["right_total"] == pytest.approx(5200.0)


def test_delta_total_base_to_final(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert result["delta_total"] == pytest.approx(3200.0)


def test_single_year_in_rows(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert len(result["rows"]) == 1


def test_row_year_is_2026(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert result["rows"][0]["year"] == 2026


def test_row_values_match_totals(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    row = result["rows"][0]
    assert row["left_value"] == pytest.approx(2000.0)
    assert row["right_value"] == pytest.approx(5200.0)
    assert row["delta"] == pytest.approx(3200.0)

# Correct aggregation — Base → Outage
def test_step_delta_base_to_outage(base_monthly, outage_monthly):
    result = compute_yearly_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    assert result["delta_total"] == pytest.approx(800.0)


def test_step_delta_outage_to_final(outage_monthly, final_monthly):
    result = compute_yearly_delta(outage_monthly, final_monthly, EV_COL, "Outage_EV", "Final_EV")
    assert result["delta_total"] == pytest.approx(2400.0)


# Consistency invariants
def test_delta_equals_right_minus_left_per_row(base_monthly, outage_monthly):
    result = compute_yearly_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    for row in result["rows"]:
        assert row["delta"] == pytest.approx(row["right_value"] - row["left_value"])


def test_delta_total_equals_right_minus_left_total(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert result["delta_total"] == pytest.approx(result["right_total"] - result["left_total"])


def test_step_deltas_sum_to_cumulative(base_monthly, outage_monthly, final_monthly):
    step1 = compute_yearly_delta(base_monthly, outage_monthly, EV_COL, "Base_EV", "Outage_EV")
    step2 = compute_yearly_delta(outage_monthly, final_monthly, EV_COL, "Outage_EV", "Final_EV")
    cumul = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert step1["delta_total"] + step2["delta_total"] == pytest.approx(cumul["delta_total"])


def test_rows_sorted_by_year(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    years = [r["year"] for r in result["rows"]]
    assert years == sorted(years)


def test_row_year_is_integer(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    for row in result["rows"]:
        assert isinstance(row["year"], int)


def test_totals_are_floats(base_monthly, final_monthly):
    result = compute_yearly_delta(base_monthly, final_monthly, EV_COL, "Base_EV", "Final_EV")
    assert isinstance(result["left_total"], float)
    assert isinstance(result["right_total"], float)
    assert isinstance(result["delta_total"], float)
