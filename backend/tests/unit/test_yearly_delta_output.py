"""Unit tests for yearly and machine-yearly delta output."""
import pandas as pd
import pytest

from backend.core.constants import (
    EV_COL,
    MACHINE_NAME_COL,
    MONTH_COL,
    SCENARIO_NAME_COL,
    TARIFF_COL,
    YEAR_COL,
)
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.yearly_delta_output import (
    compute_machine_yearly_delta,
    compute_yearly_delta,
)


def _source_df() -> pd.DataFrame:
    rows = []
    values = {
        ("Base_EV", "MACHINE_A", 2026): 10.0,
        ("Base_EV", "MACHINE_A", 2027): 20.0,
        ("Final_EV", "MACHINE_A", 2026): 15.0,
        ("Final_EV", "MACHINE_A", 2027): 25.0,
        ("Base_EV", "MACHINE_B", 2026): 100.0,
        ("Final_EV", "MACHINE_B", 2026): 80.0,
    }

    for (scenario, machine, year), value in values.items():
        for month in [5, 6]:
            for tariff in ["peak", "offpeak"]:
                rows.append({
                    SCENARIO_NAME_COL: scenario,
                    MACHINE_NAME_COL: machine,
                    YEAR_COL: year,
                    MONTH_COL: month,
                    TARIFF_COL: tariff,
                    EV_COL: value,
                })
    return pd.DataFrame(rows)


def test_yearly_delta_keeps_original_year_only_shape():
    df = _source_df()
    left = aggregate_monthly(df, ["Base_EV"], EV_COL)
    right = aggregate_monthly(df, ["Final_EV"], EV_COL)
    result = compute_yearly_delta(left, right, EV_COL, "Base_EV", "Final_EV")

    assert set(result["rows"][0]) == {"year", "left_value", "right_value", "delta"}
    assert result["rows"] == [
        {"year": 2026, "left_value": 440.0, "right_value": 380.0, "delta": -60.0},
        {"year": 2027, "left_value": 80.0, "right_value": 100.0, "delta": 20.0},
    ]
    assert result["left_total"] == pytest.approx(520.0)
    assert result["right_total"] == pytest.approx(480.0)
    assert result["delta_total"] == pytest.approx(-40.0)


def test_machine_yearly_delta_returns_machine_and_year_rows():
    result = compute_machine_yearly_delta(_source_df(), EV_COL, "Base_EV", "Final_EV")
    assert result["rows"] == [
        {
            "machine_name": "MACHINE_A",
            "year": 2026,
            "left_value": 40.0,
            "right_value": 60.0,
            "delta": 20.0,
        },
        {
            "machine_name": "MACHINE_A",
            "year": 2027,
            "left_value": 80.0,
            "right_value": 100.0,
            "delta": 20.0,
        },
        {
            "machine_name": "MACHINE_B",
            "year": 2026,
            "left_value": 400.0,
            "right_value": 320.0,
            "delta": -80.0,
        },
    ]


def test_machine_yearly_delta_machine_filter_limits_rows_and_totals():
    result = compute_machine_yearly_delta(
        _source_df(),
        EV_COL,
        "Base_EV",
        "Final_EV",
        selected_machines=["MACHINE_A"],
    )
    assert [row["machine_name"] for row in result["rows"]] == ["MACHINE_A", "MACHINE_A"]
    assert result["left_total"] == pytest.approx(120.0)
    assert result["right_total"] == pytest.approx(160.0)
    assert result["delta_total"] == pytest.approx(40.0)


def test_machine_yearly_delta_missing_right_machine_year_treated_as_zero():
    df = _source_df()
    df = df[~(
        (df[SCENARIO_NAME_COL] == "Final_EV")
        & (df[MACHINE_NAME_COL] == "MACHINE_B")
    )]
    result = compute_machine_yearly_delta(df, EV_COL, "Base_EV", "Final_EV")
    machine_b = [r for r in result["rows"] if r["machine_name"] == "MACHINE_B"][0]
    assert machine_b["left_value"] == pytest.approx(400.0)
    assert machine_b["right_value"] == pytest.approx(0.0)
    assert machine_b["delta"] == pytest.approx(-400.0)
