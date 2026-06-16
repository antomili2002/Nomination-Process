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
from backend.excel import report_writer
from backend.services import report_service
from backend.storage.processed_uploads import load_workbook_data


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
    # Load parsed artifacts once for both report computation and raw-sheet copy.
    workbook = load_workbook_data(settings.upload_dir / upload_id)

    report_data = report_service.generate_report_from_workbook(
        workbook, upload_id, iv_chain, ev_chain, selected_machines
    )

    excel_bytes = report_writer.write_report(
        report_data,
        workbook.info_df,
        workbook.raw_data_df,
    )

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scenario_report_{timestamp}.xlsx"

    return excel_bytes, filename
