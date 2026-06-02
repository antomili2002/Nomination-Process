import pandas as pd

from backend.core.constants import YEAR_COL


def compute_yearly_delta(
    left_monthly: pd.DataFrame,
    right_monthly: pd.DataFrame,
    metric: str,
    left_name: str,
    right_name: str,
) -> dict:
    """Aggregate monthly data to per-year totals and compute the delta.

    Both DataFrames come from ``aggregate_monthly()``, which already holds
    (SCENARIO_NAME, TARIFF, YEAR, MONTH) rows.  We sum over tariff and month
    so each scenario ends up with one value per year.

    Delta convention (matches the ground-truth Excel):
        delta = right_value - left_value

    The returned dict has the structure expected by ``YearlyDeltaTable``:
    {
      left_name, right_name,
      rows: [ {year, left_value, right_value, delta}, ... ],
      left_total, right_total, delta_total
    }
    """
    def _yearly(df: pd.DataFrame) -> dict[int, float]:
        return (
            df.groupby(YEAR_COL)[metric]
            .sum()
            .to_dict()
        )

    left_by_year  = _yearly(left_monthly)
    right_by_year = _yearly(right_monthly)
    years = sorted(set(left_by_year) | set(right_by_year))

    rows: list[dict] = []
    for year in years:
        lv = float(left_by_year.get(year, 0.0))
        rv = float(right_by_year.get(year, 0.0))
        rows.append({
            "year":        int(year),
            "left_value":  lv,
            "right_value": rv,
            "delta":       rv - lv,
        })

    left_total  = sum(r["left_value"]  for r in rows)
    right_total = sum(r["right_value"] for r in rows)

    return {
        "left_name":   left_name,
        "right_name":  right_name,
        "rows":        rows,
        "left_total":  float(left_total),
        "right_total": float(right_total),
        "delta_total": float(right_total - left_total),
    }
