"""Unit tests for backend/processing/scenario_extraction.py"""
import pandas as pd
import pytest

from backend.core.exceptions import ScenarioExtractionError
from backend.processing.scenario_extraction import (
    _find_header_row,
    extract_scenarios,
)


def test_finds_header_row_at_correct_position():
    df = pd.DataFrame([
        ["Some title", None, None],
        [None, None, None],
        ["Scenario Name", "Market Area", "Scenario ID"],
        ["Base_IV", "UK", 100],
    ])
    assert _find_header_row(df) == 2


def test_raises_when_sentinel_missing():
    df = pd.DataFrame([["No header here", "foo"], ["bar", "baz"]])
    with pytest.raises(ScenarioExtractionError, match="Could not find"):
        _find_header_row(df)



def test_extracts_correct_number_of_rows(info_df):
    result = extract_scenarios(info_df)
    assert len(result) == 6  # 6 scenarios in the fixture


def test_extracts_scenario_names(info_df):
    result = extract_scenarios(info_df)
    names = result["scenario_name"].tolist()
    assert "Base_IV" in names
    assert "Final_EV" in names


def test_extracts_scenario_ids(info_df):
    result = extract_scenarios(info_df)
    ids = set(result["scenario_id"].tolist())
    assert ids == {100, 101, 102, 200, 201, 202}


def test_role_is_always_none(info_df):
    # Role is not part of the standard export — always None
    result = extract_scenarios(info_df)
    assert result["role"].isna().all()


def test_indices_are_zero_based(info_df):
    result = extract_scenarios(info_df)
    assert result["index"].tolist() == list(range(6))


def test_comment_rows_are_filtered_out():
    """Rows without a valid positive Scenario ID must be dropped."""
    df = pd.DataFrame([
        [None],
        ["Scenario Name", "Market Area", "Scenario ID"],
        ["Base_IV",   "UK", 100],
        ["Outage_IV", "UK", 101],
        ["For trading of gas positions you need HCV conversion.", None, None],
        ["Another footnote row.", None, None],
    ])
    result = extract_scenarios(df)
    assert len(result) == 2
    assert set(result["scenario_id"]) == {100, 101}


def test_raises_when_no_scenario_rows():
    df = pd.DataFrame([
        [None],
        ["Scenario Name", "Market Area"],
    ])
    with pytest.raises(ScenarioExtractionError):
        extract_scenarios(df)
