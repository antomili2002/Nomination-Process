import pandas as pd

from backend.core.constants import (
    MACHINE_NAME_COL,
    MONTH_COL,
    SCENARIO_NAME_COL,
    TARIFF_COL,
    YEAR_COL,
)

# Row-level grouping keys used in the pivot table.
# MACHINE_NAME is intentionally absent: it is either pre-filtered (selected machine)
# or left to sum across all machines — matching the Excel "MACHINE_NAME: (All)" slicer.
# TARIFF is kept because peak/offpeak are distinct rows in the pivot.
_MONTHLY_GROUP_KEYS = [SCENARIO_NAME_COL, TARIFF_COL, YEAR_COL, MONTH_COL]


def aggregate_monthly(
    data_df: pd.DataFrame,
    scenario_names: list[str],
    metric: str,
    selected_machines: list[str] | None = None,
) -> pd.DataFrame:
    """Aggregate cleaned data by scenario, tariff, year, month.

    Machine handling (mirrors the Excel slicer behaviour):
      - selected_machines=None  → include all machines and sum them together
      - selected_machines=[...] → pre-filter to those machines, then sum

    Tariff is preserved as a row dimension (peak / offpeak are separate rows).

    Returns
    -------
    DataFrame with columns [SCENARIO_NAME, TARIFF, YEAR, MONTH, <metric>],
    sorted by those same keys.
    """
    df = data_df[data_df[SCENARIO_NAME_COL].isin(scenario_names)].copy()

    if selected_machines is not None:
        df = df[df[MACHINE_NAME_COL].isin(selected_machines)]

    result = (
        df.groupby(_MONTHLY_GROUP_KEYS, as_index=False)[metric]
        .sum()
        .sort_values(_MONTHLY_GROUP_KEYS)
        .reset_index(drop=True)
    )

    return result

