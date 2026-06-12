import pandas as pd
from pandas.api.types import is_numeric_dtype

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
        if col in df.columns:
            df[col] = _coerce_metric_series(df[col])
    return df


def _coerce_metric_series(series: pd.Series) -> pd.Series:
    if is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0)

    text = series.astype("string").str.strip()
    direct = pd.to_numeric(text, errors="coerce")

    comma_decimal = text.str.contains(",", regex=False, na=False)
    european_text = (
        text.str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    european = pd.to_numeric(european_text, errors="coerce")

    return direct.mask(comma_decimal, european).fillna(0.0)
