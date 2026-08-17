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
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from backend.core.config import settings
from backend.domain.layout import LAYOUT_NON_UK, layout_for_country
from backend.domain.report_metrics import REPORT_METRICS, ReportMetric, available_metrics
from backend.domain.workbook import WorkbookData
from backend.processing.chain_builder import DeltaPair, build_delta_pairs, validate_chain
from backend.processing.report_builder import (
    ReportAggregationCache,
    build_available_machines,
    build_metric_preview,
    build_metric_report,
    build_non_uk_category_sections,
)
from backend.storage.processed_uploads import load_workbook_data


# Private helpers
def _load_workbook_data(upload_id: str) -> WorkbookData:
    """Load persisted parsed workbook artifacts for an upload.

    Raises FileNotFoundError if the upload_id is unknown.
    """
    return load_workbook_data(settings.upload_dir / upload_id)


def _build_index_map(scenario_df: pd.DataFrame) -> dict[int, str]:
    return dict(zip(scenario_df["index"].tolist(), scenario_df["scenario_name"].tolist()))


def _chain_for_metric(metric: ReportMetric, iv_chain: list[int], ev_chain: list[int]) -> list[int]:
    return ev_chain if metric.chain_kind == "ev" else iv_chain


def _pairs_for_metric(
    metric: ReportMetric,
    iv_pairs: list[DeltaPair],
    ev_pairs: list[DeltaPair],
) -> list[DeltaPair]:
    return ev_pairs if metric.chain_kind == "ev" else iv_pairs


@dataclass(frozen=True)
class _ChainContext:
    """Validated, shared inputs reused by the preview and full-report builders."""
    data_df: pd.DataFrame
    index_to_name: dict[int, str]
    iv_chain: list[int]
    ev_chain: list[int]
    iv_pairs: list[DeltaPair]
    ev_pairs: list[DeltaPair]
    selected_machines: Optional[list[str]]
    cache: ReportAggregationCache


def _prepare_chain_context(
    workbook: WorkbookData,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
) -> _ChainContext:
    """Validate both chains and assemble the shared aggregation context."""
    data_df = workbook.clean_data_df
    index_to_name = _build_index_map(workbook.scenarios_df)
    available = set(index_to_name)

    validate_chain(iv_chain, available)
    validate_chain(ev_chain, available)

    return _ChainContext(
        data_df=data_df,
        index_to_name=index_to_name,
        iv_chain=iv_chain,
        ev_chain=ev_chain,
        iv_pairs=build_delta_pairs(iv_chain, index_to_name),
        ev_pairs=build_delta_pairs(ev_chain, index_to_name),
        selected_machines=selected_machines,
        cache=ReportAggregationCache(data_df, selected_machines),
    )


def _select_metrics(
    data_df: pd.DataFrame,
    selected_metrics: Optional[list[str]],
) -> tuple[ReportMetric, ...]:
    """Return every available metric, filtered to ``selected_metrics`` if given."""
    metrics = available_metrics(data_df)
    if selected_metrics is None:
        return metrics
    selected_set = set(selected_metrics)
    return tuple(m for m in metrics if m.key in selected_set)


# DataPreviewResponse still has one fixed field pair per curated metric — this
# endpoint is a live chain-configuration preview, not the dynamic metric
# selection flow, so it intentionally stays scoped to the curated 5.
_PREVIEW_FIELD_NAMES: dict[str, tuple[str, str]] = {
    "ev":        ("ev_monthly", "ev_deltas"),
    "iv":        ("iv_monthly", "iv_deltas"),
    "pp":        ("pp_monthly", "pp_deltas"),
    "iv_heat":   ("iv_heat_monthly", "iv_heat_deltas"),
    "heat_prod": ("heat_prod_monthly", "heat_prod_deltas"),
}


# Public service functions
def preview_chain(upload_id: str, iv_chain: list[int], ev_chain: list[int]) -> dict:
    """Validate chains and return the delta pairs that would be computed.

    Returns
    -------
    {"iv_pairs": [DeltaPair, ...], "ev_pairs": [DeltaPair, ...]}
    """
    workbook = _load_workbook_data(upload_id)
    index_to_name = _build_index_map(workbook.scenarios_df)
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
    workbook = _load_workbook_data(upload_id)
    return preview_data_from_workbook(workbook, iv_chain, ev_chain, selected_machines)


def preview_data_from_workbook(
    workbook: WorkbookData,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
) -> dict:
    ctx = _prepare_chain_context(workbook, iv_chain, ev_chain, selected_machines)
    result: dict = {"available_machines": build_available_machines(ctx.data_df)}
    for metric in REPORT_METRICS:
        tables = build_metric_preview(
            data_df=ctx.data_df,
            chain_indices=_chain_for_metric(metric, ctx.iv_chain, ctx.ev_chain),
            pairs=_pairs_for_metric(metric, ctx.iv_pairs, ctx.ev_pairs),
            metric=metric,
            index_to_name=ctx.index_to_name,
            selected_machines=ctx.selected_machines,
            cache=ctx.cache,
        )
        monthly_field, deltas_field = _PREVIEW_FIELD_NAMES[metric.key]
        result[monthly_field] = tables["monthly"]
        result[deltas_field] = tables["deltas"]
    return result


def generate_report(
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
    selected_metrics: Optional[list[str]] = None,
) -> dict:
    """Compute all monthly and yearly-delta tables for the configured chains.

    Returns a plain dict whose structure mirrors ``GenerateReportResponse``.
    The ``report_id`` is a freshly generated UUID.
    """
    workbook = _load_workbook_data(upload_id)
    return generate_report_from_workbook(
        workbook, upload_id, iv_chain, ev_chain, selected_machines, selected_metrics
    )


def generate_report_from_workbook(
    workbook: WorkbookData,
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
    selected_metrics: Optional[list[str]] = None,
) -> dict:
    """Build the report payload for the workbook's portfolio layout.

    The country → layout decision lives in ``layout_for_country``; each layout
    contributes only its own section list, so a new layout is added by writing a
    builder and a dispatch branch rather than editing the existing ones.
    """
    ctx = _prepare_chain_context(workbook, iv_chain, ev_chain, selected_machines)
    metrics = _select_metrics(ctx.data_df, selected_metrics)
    layout = layout_for_country(workbook.portfolio_country)

    payload: dict = {
        "report_id": str(uuid.uuid4()),
        "upload_id": upload_id,
        "portfolio_country": workbook.portfolio_country,
        "layout": layout,
        "metrics": [],
        "non_uk_sections": [],
    }
    if layout == LAYOUT_NON_UK:
        payload["non_uk_sections"] = _build_non_uk_sections(ctx, metrics)
    else:
        payload["metrics"] = _build_uk_metric_sections(ctx, metrics)
    return payload


def _build_uk_metric_sections(
    ctx: _ChainContext,
    metrics: tuple[ReportMetric, ...],
) -> list[dict]:
    """Per-metric monthly + yearly-delta tables for the UK tariff layout."""
    sections: list[dict] = []
    for metric in metrics:
        tables = build_metric_report(
            data_df=ctx.data_df,
            chain_indices=_chain_for_metric(metric, ctx.iv_chain, ctx.ev_chain),
            pairs=_pairs_for_metric(metric, ctx.iv_pairs, ctx.ev_pairs),
            metric=metric,
            index_to_name=ctx.index_to_name,
            selected_machines=ctx.selected_machines,
            cache=ctx.cache,
        )
        sections.append({
            "key": metric.key,
            "label": metric.label,
            "column": metric.column,
            "output_type": metric.output_type,
            "excel_prefix": metric.excel_prefix,
            "monthly": tables["monthly"],
            "deltas": tables["deltas"],
        })
    return sections


def _build_non_uk_sections(
    ctx: _ChainContext,
    metrics: tuple[ReportMetric, ...],
) -> list[dict]:
    """Consolidated IV/EV category tables for the non-UK layout."""
    return build_non_uk_category_sections(
        ctx.data_df,
        ctx.iv_chain,
        ctx.ev_chain,
        ctx.iv_pairs,
        ctx.ev_pairs,
        metrics,
        ctx.index_to_name,
        ctx.selected_machines,
        ctx.cache,
    )
