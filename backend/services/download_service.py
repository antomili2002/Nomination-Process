"""Business logic for the Excel download endpoint.

Orchestrates:
  1. Loading parsed workbook artifacts for the stored upload.
  2. Computing report data from the cleaned artifact.
  3. Calling the Excel writer to produce the final workbook bytes.
"""
from __future__ import annotations

import datetime
from typing import Optional

from backend.core.config import settings
from backend.domain.dimension_filters import DimensionFilters
from backend.excel import report_writer
from backend.services import report_service
from backend.storage.processed_uploads import load_workbook_data


def create_excel_report(
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
    selected_metrics: Optional[list[str]] = None,
    dimension_filters: Optional[DimensionFilters] = None,
    dimension_filters2: Optional[DimensionFilters] = None,
) -> tuple[bytes, str]:
    workbook = load_workbook_data(settings.upload_dir / upload_id)

    report_data = report_service.generate_report_from_workbook(
        workbook, upload_id, iv_chain, ev_chain, selected_machines, selected_metrics
    )

    filtered_report_data: dict | None = None
    filter_summary: dict[str, str] | None = None
    if dimension_filters and not dimension_filters.is_empty():
        filtered_report_data = report_service.generate_report_from_workbook(
            workbook, upload_id, iv_chain, ev_chain,
            None, selected_metrics, dimension_filters,
        )
        filter_summary = _build_filter_summary(dimension_filters)

    filtered_report_data2: dict | None = None
    filter_summary2: dict[str, str] | None = None
    if dimension_filters2 and not dimension_filters2.is_empty():
        filtered_report_data2 = report_service.generate_report_from_workbook(
            workbook, upload_id, iv_chain, ev_chain,
            None, selected_metrics, dimension_filters2,
        )
        filter_summary2 = _build_filter_summary(dimension_filters2)

    excel_bytes = report_writer.write_report(
        report_data,
        workbook.info_df,
        workbook.raw_data_df,
        filtered_report_data=filtered_report_data,
        filter_summary=filter_summary,
        filtered_report_data2=filtered_report_data2,
        filter_summary2=filter_summary2,
    )

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scenario_report_{timestamp}.xlsx"

    return excel_bytes, filename


def _build_filter_summary(filters: DimensionFilters) -> dict[str, str]:
    """Build a compact label → value mapping for the Excel filter header."""
    summary: dict[str, str] = {}
    for label, values in [
        ("PLANT_NAME",   filters.plant_names),
        ("UNIT_NAME",    filters.unit_names),
        ("MACHINE_NAME", filters.machine_names),
        ("FUEL_NAME",    filters.fuel_names),
    ]:
        if values is not None:
            summary[label] = values[0] if len(values) == 1 else "(Multiple Items)"
    return summary


def _build_filter_summary(filters: DimensionFilters) -> dict[str, str]:
    """Build a compact label → value mapping for the Excel filter header."""
    summary: dict[str, str] = {}
    for label, values in [
        ("PLANT_NAME",   filters.plant_names),
        ("UNIT_NAME",    filters.unit_names),
        ("MACHINE_NAME", filters.machine_names),
        ("FUEL_NAME",    filters.fuel_names),
    ]:
        if values is not None:
            summary[label] = values[0] if len(values) == 1 else "(Multiple Items)"
    return summary
