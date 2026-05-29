"""Unit tests for backend/processing/cleaning.py"""
import pandas as pd
import pytest

from backend.core.constants import (
    EV_COL, IV_COL, MACHINE_NAME_COL, MONTH_COL,
    OUTPUT_TYPE_COL, POWER_POS_COL, SCENARIO_NAME_COL,
    TARIFF_COL, YEAR_COL,
)
from backend.core.exceptions import InvalidWorkbookError
from backend.processing.cleaning import clean_data


def _minimal_row(**overrides) -> dict:
    base = {
        "SCENARIO_ID": 1,
        SCENARIO_NAME_COL: "  Base_EV  ",
        OUTPUT_TYPE_COL: "  EXTRINSIC_VALUE  ",
        YEAR_COL: "2026",
        MONTH_COL: "5",
        TARIFF_COL: "  peak  ",
        MACHINE_NAME_COL: "  MACHINE_A  ",
        POWER_POS_COL: "500",
        IV_COL: "1000",
        EV_COL: "500",
    }
    base.update(overrides)
    return base


def _df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def test_strips_whitespace_from_string_columns():
    df = _df(_minimal_row())
    result = clean_data(df)
    assert result.loc[0, SCENARIO_NAME_COL] == "Base_EV"
    assert result.loc[0, OUTPUT_TYPE_COL] == "EXTRINSIC_VALUE"
    assert result.loc[0, TARIFF_COL] == "peak"
    assert result.loc[0, MACHINE_NAME_COL] == "MACHINE_A"


def test_coerces_year_and_month_to_numeric():
    df = _df(_minimal_row(**{YEAR_COL: "2026", MONTH_COL: "5"}))
    result = clean_data(df)
    assert result.loc[0, YEAR_COL] == 2026
    assert result.loc[0, MONTH_COL] == 5


def test_metric_columns_are_float():
    df = _df(_minimal_row(**{POWER_POS_COL: "123.45", IV_COL: "0", EV_COL: "999.9"}))
    result = clean_data(df)
    assert result.loc[0, POWER_POS_COL] == pytest.approx(123.45)
    assert result.loc[0, EV_COL] == pytest.approx(999.9)


def test_decimal_comma_values_are_parsed():
    # European format: "1.234,56" means 1234.56
    df = _df(_minimal_row(**{EV_COL: "1.234,56"}))
    result = clean_data(df)
    assert result.loc[0, EV_COL] == pytest.approx(1234.56)


def test_nan_metrics_become_zero():
    df = _df(_minimal_row(**{EV_COL: "N/A"}))
    result = clean_data(df)
    assert result.loc[0, EV_COL] == 0.0


def test_raises_on_missing_required_column():
    df = _df(_minimal_row())
    df = df.drop(columns=[EV_COL])
    with pytest.raises(InvalidWorkbookError, match="missing columns"):
        clean_data(df)


def test_cleans_fixture_data_sheet(data_df):
    result = clean_data(data_df)
    assert pd.api.types.is_numeric_dtype(result[YEAR_COL])
    assert pd.api.types.is_numeric_dtype(result[EV_COL])
    assert result[SCENARIO_NAME_COL].str.contains(r"^\s").sum() == 0
