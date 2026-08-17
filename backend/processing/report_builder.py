from __future__ import annotations

from typing import Optional

import pandas as pd

from backend.core.constants import EV_COL, MACHINE_NAME_COL, MONTH_COL, YEAR_COL
from backend.domain.report_metrics import ReportMetric
from backend.processing.chain_builder import DeltaPair, build_delta_pairs
from backend.processing.delta_output import compute_delta
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.pivot import to_pivot_table
from backend.processing.yearly_delta_output import compute_yearly_delta


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
        "monthly": build_monthly_tables(
            data_df, chain_indices, metric, index_to_name, selected_machines, cache
        ),
        "deltas": build_monthly_delta_tables(
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
        "monthly": build_monthly_tables(
            data_df, chain_indices, metric, index_to_name, selected_machines, cache
        ),
        "deltas": build_yearly_delta_tables(
            data_df, pairs, metric, selected_machines, cache
        ),
    }


def build_non_uk_category_sections(
    data_df: pd.DataFrame,
    iv_chain_indices: list[int],
    ev_chain_indices: list[int],
    iv_pairs: list[DeltaPair],
    ev_pairs: list[DeltaPair],
    metrics: tuple[ReportMetric, ...],
    index_to_name: dict[int, str],
    selected_machines: Optional[list[str]],
    cache: ReportAggregationCache | None = None,
) -> list[dict]:
    """Build category tables for the non-UK layout.

    Columns: one per chain scenario, one per consecutive step delta, and
    optionally a cumulative "Total" column when the chain has > 2 scenarios.
    """
    grouped_metrics: dict[str, dict[str, list[ReportMetric]]] = {"IV": {}, "EV": {}}
    for metric in metrics:
        output_type = "EV" if metric.column == EV_COL else "IV"
        grouped_metrics[output_type].setdefault(metric.category, []).append(metric)

    sections: list[dict] = []
    for output_type, categories in grouped_metrics.items():
        chain_indices = ev_chain_indices if output_type == "EV" else iv_chain_indices
        pairs = ev_pairs if output_type == "EV" else iv_pairs
        chain_names = [index_to_name[i] for i in chain_indices]
        step_pairs = [p for p in pairs if p.pair_type == "step"]
        has_cumulative = any(p.pair_type == "cumulative" for p in pairs)

        columns = (
            [{"label": name, "kind": "scenario"} for name in chain_names]
            + [{"label": f"Delta {p.step_number}", "kind": "delta"} for p in step_pairs]
            + ([{"label": "Total", "kind": "cumulative"}] if has_cumulative else [])
        )

        for category, category_metrics in categories.items():
            sections.append({
                "output_type": output_type,
                "period": "monthly",
                "category": category,
                "columns": columns,
                "rows": _build_non_uk_rows(
                    data_df, category_metrics, chain_names, step_pairs, has_cumulative,
                    [YEAR_COL, MONTH_COL], selected_machines, cache,
                ),
            })
            sections.append({
                "output_type": output_type,
                "period": "yearly",
                "category": category,
                "columns": columns,
                "rows": _build_non_uk_rows(
                    data_df, category_metrics, chain_names, step_pairs, has_cumulative,
                    [YEAR_COL], selected_machines, cache,
                ),
            })
    return sections


def _build_non_uk_rows(
    data_df: pd.DataFrame,
    metrics: list[ReportMetric],
    chain_names: list[str],
    step_pairs: list[DeltaPair],
    has_cumulative: bool,
    date_columns: list[str],
    selected_machines: Optional[list[str]],
    cache: ReportAggregationCache | None,
) -> list[dict]:
    rows: list[dict] = []
    for metric in metrics:
        scenario_value_map: dict[str, dict[tuple[int, ...], float]] = {
            name: _group_non_uk_values(
                _agg(data_df, [name], metric.column, selected_machines, cache),
                metric.column,
                date_columns,
            )
            for name in chain_names
        }

        all_date_keys = sorted(
            set().union(*[set(sv.keys()) for sv in scenario_value_map.values()])
        )

        for date_key in all_date_keys:
            scen_vals = [scenario_value_map[name].get(date_key, 0.0) for name in chain_names]
            step_delta_vals = [
                scenario_value_map[p.right_name].get(date_key, 0.0)
                - scenario_value_map[p.left_name].get(date_key, 0.0)
                for p in step_pairs
            ]
            values = scen_vals + step_delta_vals
            if has_cumulative:
                values.append(scen_vals[-1] - scen_vals[0])

            row: dict = {
                "metric_key": metric.key,
                "metric_label": metric.label,
                "metric_column": metric.column,
                "values": values,
            }
            row.update(dict(zip((col.lower() for col in date_columns), date_key)))
            rows.append(row)
    return rows


def _group_non_uk_values(
    monthly_data: pd.DataFrame,
    metric_column: str,
    date_columns: list[str],
) -> dict[tuple[int, ...], float]:
    grouped = monthly_data.groupby(date_columns)[metric_column].sum()
    return {
        tuple(int(value) for value in key if value is not None)
        if isinstance(key, tuple)
        else (int(key),): float(value)
        for key, value in grouped.items()
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
