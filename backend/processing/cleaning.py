import pandas as pd

from backend.core.constants import (
    MACHINE_NAME_COL,
    METRIC_COLS,
    MONTH_COL,
    OUTPUT_TYPE_COL,
    REQUIRED_DATA_COLS,
    SCENARIO_NAME_COL,
    TARIFF_COL,
    YEAR_COL,
)
from backend.core.exceptions import InvalidWorkbookError


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned copy of the raw Data sheet DataFrame."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    _assert_required_columns(df)
    df = _clean_string_columns(df)
    df = _coerce_year_month(df)
    df = _coerce_metric_columns(df)
    return df


def _assert_required_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_DATA_COLS if c not in df.columns]
    if missing:
        raise InvalidWorkbookError(f"Data sheet is missing columns: {missing}")


def _clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in [SCENARIO_NAME_COL, OUTPUT_TYPE_COL, TARIFF_COL, MACHINE_NAME_COL]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def _coerce_year_month(df: pd.DataFrame) -> pd.DataFrame:
    for col in [YEAR_COL, MONTH_COL]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _coerce_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Handle decimal-comma strings and convert metrics to float."""
    for col in METRIC_COLS:
        if col not in df.columns:
            continue
        if df[col].dtype != object:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            continue
        # Try standard numeric conversion first
        direct = pd.to_numeric(df[col], errors="coerce")
        new_nans = direct.isna().sum() - df[col].isna().sum()
        if new_nans == 0:
            # No parsing failures — column is already in standard format
            df[col] = direct.fillna(0.0)
        else:
            # Fall back to European decimal-comma format: "1.234,56" → 1234.56
            converted = (
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[col] = pd.to_numeric(converted, errors="coerce").fillna(0.0)
    return df
