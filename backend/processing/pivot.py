"""Convert tidy aggregated DataFrames into JSON-ready pivot structures.

The pivot format mirrors the ground-truth Excel layout:
  columns = month numbers (1-12, only those present in data)
  rows    = (year, tariff) pairs with a list of values aligned to columns
  title   = scenario name or delta pair label
"""
from __future__ import annotations

import pandas as pd

from backend.core.constants import MONTH_COL, SCENARIO_NAME_COL, TARIFF_COL, YEAR_COL


def to_pivot_table(df: pd.DataFrame, metric: str) -> dict:
    """Convert a tidy monthly DataFrame into a pivot table dict.

    Each row in the result represents one (year, tariff) combination.
    Values are aligned to the sorted list of months present in the data.

    Returns
    -------
    {
        "months": [5, 6],            # sorted distinct months
        "scenario": "Base_EV",       # first scenario name found (or pair label)
        "rows": [
            {"year": 2026, "tariff": "offpeak", "values": [500.0, 500.0]},
            {"year": 2026, "tariff": "peak",    "values": [500.0, 500.0]},
        ]
    }
    """
    months: list[int] = sorted(df[MONTH_COL].unique().tolist())
    scenario_name = df[SCENARIO_NAME_COL].iloc[0] if not df.empty else ""

    rows: list[dict] = []
    for (year, tariff), group in df.groupby([YEAR_COL, TARIFF_COL]):
        month_to_value = dict(
            zip(group[MONTH_COL].tolist(), group[metric].tolist())
        )
        values = [float(month_to_value.get(m, 0.0)) for m in months]
        rows.append({"year": int(year), "tariff": str(tariff), "values": values})

    rows.sort(key=lambda r: (r["year"], r["tariff"]))

    return {
        "months": months,
        "scenario": scenario_name,
        "rows": rows,
    }
