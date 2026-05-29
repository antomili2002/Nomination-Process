import pandas as pd

from backend.core.constants import (
    INFO_COL_MARKET_AREA,
    INFO_COL_SCENARIO_ID,
    INFO_COL_SCENARIO_NAME,
    INFO_COL_SCENARIO_TYPE,
    INFO_COL_STATUS,
    INFO_HEADER_SENTINEL,
)
from backend.core.exceptions import ScenarioExtractionError


def extract_scenarios(info_df: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy DataFrame of scenario rows from the raw Info sheet.

    Columns returned: index (0-based), scenario_name, scenario_id,
    market_area, scenario_type, status, role (always None).
    """
    header_row_idx = _find_header_row(info_df)
    raw = _slice_scenario_table(info_df, header_row_idx)
    return _build_scenario_df(raw)


#helpers for extract_scenarios
def _find_header_row(df: pd.DataFrame) -> int:
    """Return the integer row index of the row that contains ''Scenario Name''."""
    for i, row in df.iterrows():
        if any(str(v).strip() == INFO_HEADER_SENTINEL for v in row):
            return int(i)
    raise ScenarioExtractionError(
        f"Could not find a row containing ''{INFO_HEADER_SENTINEL}'' in the Info sheet."
    )


def _slice_scenario_table(df: pd.DataFrame, header_row_idx: int) -> pd.DataFrame:
    """Return only genuine scenario rows from below the header.

    A row is a real scenario if:
    - ''Scenario Name'' is non-blank, AND
    - ''Scenario ID'' parses to a positive integer.

    This discards comment/footnote rows that sometimes appear after the
    scenario table in the Info sheet.
    """
    header = [str(v).strip() for v in df.iloc[header_row_idx]]
    data = df.iloc[header_row_idx + 1 :].copy()
    data.columns = header
    data = data.reset_index(drop=True)

    name_col = INFO_COL_SCENARIO_NAME
    if name_col not in data.columns:
        raise ScenarioExtractionError(
            f"No ''{name_col}'' column found after the header row."
        )

    has_name = data[name_col].notna() & (data[name_col].astype(str).str.strip() != "")
    data = data[has_name].reset_index(drop=True)

    # Drop rows whose Scenario ID is missing or zero — those are comment rows
    if INFO_COL_SCENARIO_ID in data.columns:
        numeric_id = pd.to_numeric(data[INFO_COL_SCENARIO_ID], errors="coerce")
        data = data[numeric_id.notna() & (numeric_id > 0)].reset_index(drop=True)

    if data.empty:
        raise ScenarioExtractionError("No valid scenario rows found in the Info sheet.")

    return data


def _build_scenario_df(raw: pd.DataFrame) -> pd.DataFrame:
    """Map raw Info columns to a canonical scenario DataFrame."""
    rows = []
    for i, row in raw.iterrows():
        rows.append(
            {
                "index": int(i),
                "scenario_name": str(row.get(INFO_COL_SCENARIO_NAME, "")).strip(),
                "scenario_id": _parse_scenario_id(row.get(INFO_COL_SCENARIO_ID)),
                "market_area": str(row.get(INFO_COL_MARKET_AREA, "")).strip(),
                "scenario_type": str(row.get(INFO_COL_SCENARIO_TYPE, "")).strip(),
                "status": str(row.get(INFO_COL_STATUS, "")).strip(),
                "role": None,
            }
        )

    return pd.DataFrame(rows)


def _parse_scenario_id(value: object) -> int:
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return 0
