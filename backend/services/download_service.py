"""Business logic for the Excel download endpoint.

Orchestrates:
  1. Recomputing the report data from the stored upload.
  2. Reading the Info / Data sheets from the same upload.
  3. Calling the Excel writer to produce the final workbook bytes.
"""
from __future__ import annotations

import datetime
from typing import Optional

from backend.excel import report_writer
from backend.processing.readers import read_workbook_sheets
from backend.services import report_service
from backend.storage.temp_files import get_upload_path


def create_excel_report(
    upload_id: str,
    iv_chain: list[int],
    ev_chain: list[int],
    selected_machines: Optional[list[str]],
) -> tuple[bytes, str]:
    """Generate the full Excel report and return ``(excel_bytes, filename)``.

    Raises
    ------
    FileNotFoundError
        If *upload_id* is unknown (upload expired or never existed).
    InvalidChainError / InvalidWorkbookError / ScenarioExtractionError
        Propagated from the underlying service layer.
    """
    # Load Info and Data sheets for copying into the output workbook.
    path = get_upload_path(upload_id)
    info_df, data_df = read_workbook_sheets(path)

    # Recompute the pivot/delta data (same logic as the /generate endpoint).
    report_data = report_service.generate_report(
        upload_id, iv_chain, ev_chain, selected_machines
    )

    excel_bytes = report_writer.write_report(report_data, info_df, data_df)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scenario_report_{timestamp}.xlsx"

    return excel_bytes, filename
