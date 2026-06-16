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

from backend.core.config import settings
from backend.domain.report_metrics import REPORT_METRICS, ReportMetric
from backend.domain.workbook import WorkbookData
from backend.processing.chain_builder import DeltaPair, build_delta_pairs, validate_chain
from backend.processing.report_builder import (
    ReportAggregationCache,
    build_available_machines,
    build_metric_preview,
    build_metric_report,
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
    data_df = workbook.clean_data_df
    index_to_name = _build_index_map(workbook.scenarios_df)
    available = set(index_to_name)

    validate_chain(iv_chain, available)
    validate_chain(ev_chain, available)

    iv_pairs = build_delta_pairs(iv_chain, index_to_name)
    ev_pairs = build_delta_pairs(ev_chain, index_to_name)
    cache = ReportAggregationCache(data_df, selected_machines)
    result: dict = {"available_machines": build_available_machines(data_df)}
    for metric in REPORT_METRICS:
        result.update(build_metric_preview(
            data_df=data_df,
            chain_indices=_chain_for_metric(metric, iv_chain, ev_chain),
            pairs=_pairs_for_metric(metric, iv_pairs, ev_pairs),
            metric=metric,
            index_to_name=index_to_name,
            selected_machines=selected_machines,
            cache=cache,
        ))
    return result


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
    workbook = _load_workbook_data(upload_id)
    return generate_report_from_workbook(
        workbook, upload_id, iv_chain, ev_chain, selected_machines
    )


def generate_report_from_workbook(
    workbook: WorkbookData,
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
) -> dict:
    data_df = workbook.clean_data_df
    index_to_name = _build_index_map(workbook.scenarios_df)
    available = set(index_to_name)

    validate_chain(iv_chain, available)
    validate_chain(ev_chain, available)

    iv_pairs = build_delta_pairs(iv_chain, index_to_name)
    ev_pairs = build_delta_pairs(ev_chain, index_to_name)
    cache = ReportAggregationCache(data_df, selected_machines)
    result: dict = {
        "report_id":  str(uuid.uuid4()),
        "upload_id":  upload_id,
    }
    for metric in REPORT_METRICS:
        result.update(build_metric_report(
            data_df=data_df,
            chain_indices=_chain_for_metric(metric, iv_chain, ev_chain),
            pairs=_pairs_for_metric(metric, iv_pairs, ev_pairs),
            metric=metric,
            index_to_name=index_to_name,
            selected_machines=selected_machines,
            cache=cache,
        ))
    return result
