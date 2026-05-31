import pandas as pd

from backend.core.constants import MONTH_COL, SCENARIO_NAME_COL, TARIFF_COL, YEAR_COL

# Keys used to align the left and right monthly tables before subtracting.
# SCENARIO_NAME is excluded intentionally — each DataFrame has its own scenario.
_MERGE_KEYS = [TARIFF_COL, YEAR_COL, MONTH_COL]


def compute_delta(
    left_monthly: pd.DataFrame,
    right_monthly: pd.DataFrame,
    metric: str,
    left_name: str,
    right_name: str,
) -> pd.DataFrame:
    """Compute the per-cell delta between two aggregated monthly DataFrames.

    delta = right_value - left_value

    This encodes the *cumulative* nature of the chains: each right scenario
    already contains everything the left scenario had, plus its own additions.
    So the delta isolates exactly what the right scenario contributed on top.

    Both DataFrames must come from aggregate_monthly() and share the same
    (tariff, year, month) key space.  Combinations present in one but not the
    other are filled with 0 before subtracting (treat missing as no value).

    Parameters
    ----------
    left_monthly  : aggregated monthly DataFrame for the reference scenario
    right_monthly : aggregated monthly DataFrame for the new scenario
    metric        : metric column (e.g. EV_COL)
    left_name     : display name written into SCENARIO_NAME_COL of the result
    right_name    : display name written into SCENARIO_NAME_COL of the result
                    Format: "<left_name> → <right_name>" so the caller can label
                    the delta table clearly.

    Returns
    -------
    DataFrame with columns [SCENARIO_NAME, TARIFF, YEAR, MONTH, <metric>]
    where <metric> holds the delta value and SCENARIO_NAME encodes the pair.
    """
    left = left_monthly[_MERGE_KEYS + [metric]].rename(columns={metric: "_left"})
    right = right_monthly[_MERGE_KEYS + [metric]].rename(columns={metric: "_right"})

    merged = pd.merge(left, right, on=_MERGE_KEYS, how="outer")
    merged["_left"] = pd.to_numeric(merged["_left"], errors="coerce").fillna(0.0)
    merged["_right"] = pd.to_numeric(merged["_right"], errors="coerce").fillna(0.0)

    result = merged[_MERGE_KEYS].copy()
    result[metric] = merged["_right"] - merged["_left"]
    result[SCENARIO_NAME_COL] = f"{left_name} → {right_name}"

    col_order = [SCENARIO_NAME_COL] + _MERGE_KEYS + [metric]
    return (
        result[col_order]
        .sort_values(_MERGE_KEYS)
        .reset_index(drop=True)
    )
