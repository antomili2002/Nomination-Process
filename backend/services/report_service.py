"""Business logic for the report generation pipeline.

Controllers are pure HTTP adapters: they validate request inputs, call these
service functions, and map the returned plain-Python data to response schemas.

All domain exceptions propagate to the caller:
  FileNotFoundError         → upload not found     → HTTP 404
  InvalidWorkbookError      → bad Excel structure  → HTTP 422
  ScenarioExtractionError   → no scenario rows     → HTTP 422
  InvalidChainError         → bad chain indices    → HTTP 422
"""
from __future__ import annotations

import uuid
from typing import Optional

import pandas as pd

from backend.core.constants import EV_COL, IV_COL, MACHINE_NAME_COL, POWER_POS_COL
from backend.processing.chain_builder import DeltaPair, build_delta_pairs, validate_chain
from backend.processing.cleaning import clean_data
from backend.processing.delta_output import compute_delta
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.pivot import to_pivot_table
from backend.processing.readers import read_workbook_sheets
from backend.processing.scenario_extraction import extract_scenarios
from backend.processing.yearly_delta_output import compute_machine_yearly_delta, compute_yearly_delta
from backend.storage.temp_files import get_upload_path


# Private helpers
def _load_workbook(upload_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the workbook and return (info_df, data_df).

    Raises FileNotFoundError if the upload_id is unknown.
    """
    path = get_upload_path(upload_id)
    return read_workbook_sheets(path)


def _build_index_map(info_df: pd.DataFrame) -> dict[int, str]:
    scenario_df = extract_scenarios(info_df)
    return dict(zip(scenario_df["index"].tolist(), scenario_df["scenario_name"].tolist()))


def _agg(
    data_df: pd.DataFrame,
    scenario_names: list[str],
    metric: str,
    selected_machines: Optional[list[str]],
) -> pd.DataFrame:
    return aggregate_monthly(data_df, scenario_names, metric, selected_machines=selected_machines)


def _monthly_pivot_tables(
    data_df: pd.DataFrame,
    chain_indices: list[int],
    metric: str,
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
) -> list[dict]:
    """Return pivot-table dicts for the base and final scenario of a chain."""
    tables = []
    for idx in [chain_indices[0], chain_indices[-1]]:
        name = index_to_name[idx]
        raw = to_pivot_table(_agg(data_df, [name], metric, selected_machines), metric)
        tables.append({"title": name, "months": raw["months"], "rows": raw["rows"]})
    return tables


def _delta_pivot_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: str,
    selected_machines: Optional[list[str]],
) -> list[dict]:
    """Monthly-delta pivot tables (for data-preview only)."""
    tables = []
    for p in pairs:
        left_df = _agg(data_df, [p.left_name], metric, selected_machines)
        right_df = _agg(data_df, [p.right_name], metric, selected_machines)
        delta_df = compute_delta(left_df, right_df, metric, p.left_name, p.right_name)
        raw = to_pivot_table(delta_df, metric)
        tables.append({
            "title": f"{p.left_name} \u2192 {p.right_name}",
            "pair_type": p.pair_type,
            "step_number": p.step_number,
            "months": raw["months"],
            "rows": raw["rows"],
        })
    return tables


def _yearly_delta_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: str,
    selected_machines: Optional[list[str]],
) -> list[dict]:
    """Yearly-aggregate delta tables (for the generate endpoint)."""
    tables = []
    for p in pairs:
        left_df = _agg(data_df, [p.left_name], metric, selected_machines)
        right_df = _agg(data_df, [p.right_name], metric, selected_machines)
        d = compute_yearly_delta(left_df, right_df, metric, p.left_name, p.right_name)
        tables.append({
            **d,
            "pair_type": p.pair_type,
            "step_number": p.step_number,
        })
    return tables


def _machine_yearly_delta_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: str,
    selected_machines: Optional[list[str]],
) -> list[dict]:
    """Machine/year aggregate delta tables (for generate and export)."""
    tables = []
    for p in pairs:
        d = compute_machine_yearly_delta(data_df, metric, p.left_name, p.right_name, selected_machines)
        tables.append({
            **d,
            "pair_type": p.pair_type,
            "step_number": p.step_number,
        })
    return tables


# Public service functions
def preview_chain(upload_id: str, iv_chain: list[int], ev_chain: list[int]) -> dict:
    """Validate chains and return the delta pairs that would be computed.

    Returns
    -------
    {"iv_pairs": [DeltaPair, ...], "ev_pairs": [DeltaPair, ...]}
    """
    info_df, _ = _load_workbook(upload_id)
    index_to_name = _build_index_map(info_df)
    available = set(index_to_name)

    validate_chain(iv_chain, available)
    validate_chain(ev_chain, available)

    return {
        "iv_pairs": build_delta_pairs(iv_chain, index_to_name),
        "ev_pairs": build_delta_pairs(ev_chain, index_to_name),
    }


def preview_data(
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
) -> dict:
    """Compute monthly + monthly-delta pivot tables for the live preview.

    Returns a plain dict whose structure mirrors ``DataPreviewResponse``.
    """
    info_df, data_df = _load_workbook(upload_id)
    data_df = clean_data(data_df)
    index_to_name = _build_index_map(info_df)
    available = set(index_to_name)

    validate_chain(iv_chain, available)
    validate_chain(ev_chain, available)

    iv_pairs = build_delta_pairs(iv_chain, index_to_name)
    ev_pairs = build_delta_pairs(ev_chain, index_to_name)
    sel = selected_machines
    machines: list[str] = sorted(data_df[MACHINE_NAME_COL].dropna().unique().tolist())

    return {
        "available_machines": machines,
        "ev_monthly": _monthly_pivot_tables(data_df, ev_chain, EV_COL, index_to_name, sel),
        "ev_deltas":  _delta_pivot_tables(data_df, ev_pairs, EV_COL, sel),
        "iv_monthly": _monthly_pivot_tables(data_df, iv_chain, IV_COL, index_to_name, sel),
        "iv_deltas":  _delta_pivot_tables(data_df, iv_pairs, IV_COL, sel),
        "pp_monthly": _monthly_pivot_tables(data_df, iv_chain, POWER_POS_COL, index_to_name, sel),
    }


def generate_report(
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
) -> dict:
    """Compute all monthly and yearly-delta tables for the configured chains.

    Returns a plain dict whose structure mirrors ``GenerateReportResponse``.
    The ``report_id`` is a freshly generated UUID.
    """
    info_df, data_df = _load_workbook(upload_id)
    data_df = clean_data(data_df)
    index_to_name = _build_index_map(info_df)
    available = set(index_to_name)

    validate_chain(iv_chain, available)
    validate_chain(ev_chain, available)

    iv_pairs = build_delta_pairs(iv_chain, index_to_name)
    ev_pairs = build_delta_pairs(ev_chain, index_to_name)
    sel = selected_machines

    return {
        "report_id":  str(uuid.uuid4()),
        "upload_id":  upload_id,
        "ev_monthly": _monthly_pivot_tables(data_df, ev_chain, EV_COL, index_to_name, sel),
        "ev_deltas":  _yearly_delta_tables(data_df, ev_pairs, EV_COL, sel),
        "ev_machine_deltas": _machine_yearly_delta_tables(data_df, ev_pairs, EV_COL, sel),
        "iv_monthly": _monthly_pivot_tables(data_df, iv_chain, IV_COL, index_to_name, sel),
        "iv_deltas":  _yearly_delta_tables(data_df, iv_pairs, IV_COL, sel),
        "iv_machine_deltas": _machine_yearly_delta_tables(data_df, iv_pairs, IV_COL, sel),
        "pp_monthly": _monthly_pivot_tables(data_df, iv_chain, POWER_POS_COL, index_to_name, sel),
        "pp_deltas":  _yearly_delta_tables(data_df, iv_pairs, POWER_POS_COL, sel),
        "pp_machine_deltas": _machine_yearly_delta_tables(data_df, iv_pairs, POWER_POS_COL, sel),
    }
