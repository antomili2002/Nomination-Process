from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.core.constants import MACHINE_NAME_COL, SCENARIO_NAME_COL, YEAR_COL
from backend.domain.report_metrics import ReportMetric
from backend.processing.chain_builder import DeltaPair
from backend.processing.delta_output import compute_delta
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.pivot import to_pivot_table
from backend.processing.yearly_delta_output import (
    compute_machine_yearly_delta,
    compute_yearly_delta,
)


class ReportAggregationCache:
    """Request-scoped cache for repeated scenario/metric aggregations."""

    def __init__(
        self,
        data_df: pd.DataFrame,
        selected_machines: Optional[list[str]],
    ) -> None:
        self._data_df = data_df
        self._selected_machines = selected_machines
        self._monthly: dict[tuple[tuple[str, ...], str], pd.DataFrame] = {}
        self._machine_yearly: dict[tuple[str, str], dict[tuple[str, int], float]] = {}

    def monthly(self, scenario_names: list[str], metric_col: str) -> pd.DataFrame:
        key = (tuple(scenario_names), metric_col)
        if key not in self._monthly:
            self._monthly[key] = aggregate_monthly(
                self._data_df,
                scenario_names,
                metric_col,
                selected_machines=self._selected_machines,
            )
        return self._monthly[key]

    def machine_yearly(
        self,
        scenario_name: str,
        metric_col: str,
    ) -> dict[tuple[str, int], float]:
        key = (scenario_name, metric_col)
        if key not in self._machine_yearly:
            df = self._data_df[self._data_df[SCENARIO_NAME_COL] == scenario_name]
            if self._selected_machines is not None:
                df = df[df[MACHINE_NAME_COL].isin(self._selected_machines)]
            if df.empty:
                self._machine_yearly[key] = {}
            else:
                self._machine_yearly[key] = (
                    df.groupby([MACHINE_NAME_COL, YEAR_COL])[metric_col]
                    .sum()
                    .to_dict()
                )
        return self._machine_yearly[key]


def build_metric_preview(
    data_df: pd.DataFrame,
    chain_indices: list[int],
    pairs: list[DeltaPair],
    metric: ReportMetric,
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
    cache: ReportAggregationCache | None = None,
) -> dict[str, list[dict]]:
    return {
        metric.monthly_field: build_monthly_tables(
            data_df, chain_indices, metric, index_to_name, selected_machines, cache
        ),
        metric.deltas_field: build_monthly_delta_tables(
            data_df, pairs, metric, selected_machines, cache
        ),
    }


def build_metric_report(
    data_df: pd.DataFrame,
    chain_indices: list[int],
    pairs: list[DeltaPair],
    metric: ReportMetric,
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
    cache: ReportAggregationCache | None = None,
) -> dict[str, list[dict]]:
    return {
        metric.monthly_field: build_monthly_tables(
            data_df, chain_indices, metric, index_to_name, selected_machines, cache
        ),
        metric.deltas_field: build_yearly_delta_tables(
            data_df, pairs, metric, selected_machines, cache
        ),
        metric.machine_deltas_field: build_machine_yearly_delta_tables(
            data_df, pairs, metric, selected_machines, cache
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
    cache: ReportAggregationCache | None = None,
) -> list[dict]:
    tables = []
    for idx in [chain_indices[0], chain_indices[-1]]:
        name = index_to_name[idx]
        raw = to_pivot_table(
            _agg(data_df, [name], metric.column, selected_machines, cache),
            metric.column,
        )
        tables.append({"title": name, "months": raw["months"], "rows": raw["rows"]})
    return tables


def build_monthly_delta_tables(
    data_df: pd.DataFrame,
    pairs: list[DeltaPair],
    metric: ReportMetric,
    selected_machines: Optional[list[str]],
    cache: ReportAggregationCache | None = None,
) -> list[dict]:
    tables = []
    for pair in pairs:
        left_df = _agg(
            data_df, [pair.left_name], metric.column, selected_machines, cache
        )
        right_df = _agg(
            data_df, [pair.right_name], metric.column, selected_machines, cache
        )
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
    cache: ReportAggregationCache | None = None,
) -> list[dict]:
    tables = []
    for pair in pairs:
        left_df = _agg(
            data_df, [pair.left_name], metric.column, selected_machines, cache
        )
        right_df = _agg(
            data_df, [pair.right_name], metric.column, selected_machines, cache
        )
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
    cache: ReportAggregationCache | None = None,
) -> list[dict]:
    tables = []
    for pair in pairs:
        if cache is None:
            delta = compute_machine_yearly_delta(
                data_df,
                metric.column,
                pair.left_name,
                pair.right_name,
                selected_machines,
            )
        else:
            delta = _machine_yearly_delta_from_cache(
                cache, metric.column, pair.left_name, pair.right_name
            )
        tables.append({
            **delta,
            "pair_type": pair.pair_type,
            "step_number": pair.step_number,
        })
    return tables


def _machine_yearly_delta_from_cache(
    cache: ReportAggregationCache,
    metric: str,
    left_name: str,
    right_name: str,
) -> dict:
    left_by_key = cache.machine_yearly(left_name, metric)
    right_by_key = cache.machine_yearly(right_name, metric)
    keys = sorted(
        set(left_by_key) | set(right_by_key),
        key=lambda k: (str(k[0]), int(k[1])),
    )

    rows: list[dict] = []
    for machine_name, year in keys:
        lv = float(left_by_key.get((machine_name, year), 0.0))
        rv = float(right_by_key.get((machine_name, year), 0.0))
        rows.append({
            "machine_name": str(machine_name),
            "year": int(year),
            "left_value": lv,
            "right_value": rv,
            "delta": rv - lv,
        })

    left_total = sum(r["left_value"] for r in rows)
    right_total = sum(r["right_value"] for r in rows)

    return {
        "left_name": left_name,
        "right_name": right_name,
        "rows": rows,
        "left_total": float(left_total),
        "right_total": float(right_total),
        "delta_total": float(right_total - left_total),
    }


def _agg(
    data_df: pd.DataFrame,
    scenario_names: list[str],
    metric_col: str,
    selected_machines: Optional[list[str]],
    cache: ReportAggregationCache | None = None,
) -> pd.DataFrame:
    if cache is not None:
        return cache.monthly(scenario_names, metric_col)
    return aggregate_monthly(
        data_df, scenario_names, metric_col, selected_machines=selected_machines
    )
