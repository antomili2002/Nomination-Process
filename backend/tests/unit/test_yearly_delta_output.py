"""Unit tests for yearly delta output."""
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
from backend.processing.yearly_delta_output import compute_yearly_delta


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
