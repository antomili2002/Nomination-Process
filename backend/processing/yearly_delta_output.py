import pandas as pd

from backend.core.constants import MACHINE_NAME_COL, SCENARIO_NAME_COL, YEAR_COL


def compute_yearly_delta(
    left_monthly: pd.DataFrame,
    right_monthly: pd.DataFrame,
    metric: str,
    left_name: str,
    right_name: str,
) -> dict:
    """Aggregate monthly data to per-year totals and compute the delta."""
    def _yearly(df: pd.DataFrame) -> dict[int, float]:
        return (
            df.groupby(YEAR_COL)[metric]
            .sum()
            .to_dict()
        )

    left_by_year = _yearly(left_monthly)
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

    left_total = sum(r["left_value"] for r in rows)
    right_total = sum(r["right_value"] for r in rows)

    return {
        "left_name":   left_name,
        "right_name":  right_name,
        "rows":        rows,
        "left_total":  float(left_total),
        "right_total": float(right_total),
        "delta_total": float(right_total - left_total),
    }


def compute_machine_yearly_delta(
    data_df: pd.DataFrame,
    metric: str,
    left_name: str,
    right_name: str,
    selected_machines: list[str] | None = None,
) -> dict:
    """Aggregate source data to per-machine yearly totals and compute delta."""
    def _yearly(scenario_name: str) -> dict[tuple[str, int], float]:
        df = data_df[data_df[SCENARIO_NAME_COL] == scenario_name].copy()
        if selected_machines is not None:
            df = df[df[MACHINE_NAME_COL].isin(selected_machines)]
        if df.empty:
            return {}
        return (
            df.groupby([MACHINE_NAME_COL, YEAR_COL])[metric]
            .sum()
            .to_dict()
        )

    left_by_key = _yearly(left_name)
    right_by_key = _yearly(right_name)
    keys = sorted(set(left_by_key) | set(right_by_key), key=lambda k: (str(k[0]), int(k[1])))

    rows: list[dict] = []
    for machine_name, year in keys:
        lv = float(left_by_key.get((machine_name, year), 0.0))
        rv = float(right_by_key.get((machine_name, year), 0.0))
        rows.append({
            "machine_name": str(machine_name),
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
