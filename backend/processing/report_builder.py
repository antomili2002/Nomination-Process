from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.core.constants import MACHINE_NAME_COL
from backend.domain.report_metrics import ReportMetric
from backend.processing.chain_builder import DeltaPair
from backend.processing.delta_output import compute_delta
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.pivot import to_pivot_table
from backend.processing.yearly_delta_output import (
    compute_machine_yearly_delta,
    compute_yearly_delta,
)


def build_metric_preview(
    data_df: pd.DataFrame,
    chain_indices: list[int],
    pairs: list[DeltaPair],
    metric: ReportMetric,
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
) -> dict[str, list[dict]]:
    return {
        metric.monthly_field: build_monthly_tables(
            data_df, chain_indices, metric, index_to_name, selected_machines
        ),
        metric.deltas_field: build_monthly_delta_tables(
            data_df, pairs, metric, selected_machines
        ),
    }


def build_metric_report(
    data_df: pd.DataFrame,
    chain_indices: list[int],
    pairs: list[DeltaPair],
    metric: ReportMetric,
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
) -> dict[str, list[dict]]:
    return {
        metric.monthly_field: build_monthly_tables(
            data_df, chain_indices, metric, index_to_name, selected_machines
        ),
        metric.deltas_field: build_yearly_delta_tables(
            data_df, pairs, metric, selected_machines
        ),
        metric.machine_deltas_field: build_machine_yearly_delta_tables(
            data_df, pairs, metric, selected_machines
        ),
    }


def build_available_machines(data_df: pd.DataFrame) -> list[str]:
    return sorted(data_df[MACHINE_NAME_COL].dropna().unique().tolist())


def build_monthly_tables(
    data_df: pd.DataFrame,
    chain_indices: list[int],
    metric: ReportMetric,
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
) -> list[dict]:
    tables = []
    for idx in [chain_indices[0], chain_indices[-1]]:
        name = index_to_name[idx]
        raw = to_pivot_table(
            _agg(data_df, [name], metric.column, selected_machines),
            metric.column,
        )
        tables.append({"title": name, "months": raw["months"], "rows": raw["rows"]})
    return tables


def build_monthly_delta_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: ReportMetric,
    selected_machines: Optional[list[str]],
) -> list[dict]:
    tables = []
    for pair in pairs:
        left_df = _agg(data_df, [pair.left_name], metric.column, selected_machines)
        right_df = _agg(data_df, [pair.right_name], metric.column, selected_machines)
        delta_df = compute_delta(
            left_df, right_df, metric.column, pair.left_name, pair.right_name
        )
        raw = to_pivot_table(delta_df, metric.column)
        tables.append({
            "title": f"{pair.left_name} \u2192 {pair.right_name}",
            "pair_type": pair.pair_type,
            "step_number": pair.step_number,
            "months": raw["months"],
            "rows": raw["rows"],
        })
    return tables


def build_yearly_delta_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: ReportMetric,
    selected_machines: Optional[list[str]],
) -> list[dict]:
    tables = []
    for pair in pairs:
        left_df = _agg(data_df, [pair.left_name], metric.column, selected_machines)
        right_df = _agg(data_df, [pair.right_name], metric.column, selected_machines)
        delta = compute_yearly_delta(
            left_df, right_df, metric.column, pair.left_name, pair.right_name
        )
        tables.append({
            **delta,
            "pair_type": pair.pair_type,
            "step_number": pair.step_number,
        })
    return tables


def build_machine_yearly_delta_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: ReportMetric,
    selected_machines: Optional[list[str]],
) -> list[dict]:
    tables = []
    for pair in pairs:
        delta = compute_machine_yearly_delta(
            data_df, metric.column, pair.left_name, pair.right_name, selected_machines
        )
        tables.append({
            **delta,
            "pair_type": pair.pair_type,
            "step_number": pair.step_number,
        })
    return tables


def _agg(
    data_df: pd.DataFrame,
    scenario_names: list[str],
    metric_col: str,
    selected_machines: Optional[list[str]],
) -> pd.DataFrame:
    return aggregate_monthly(
        data_df, scenario_names, metric_col, selected_machines=selected_machines
    )
