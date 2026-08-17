from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.domain.report_metrics import ReportMetric


@dataclass(frozen=True)
class ScenarioInfo:
    index: int
    scenario_name: str
    scenario_id: int
    market_area: str = ""
    scenario_type: str = ""
    status: str = ""
    role: str | None = None


@dataclass(frozen=True)
class UploadedWorkbook:
    upload_id: str
    file_name: str
    scenarios: list[ScenarioInfo]
    machines: list[str]
    available_metrics: list[ReportMetric]


@dataclass(frozen=True)
class WorkbookData:
    info_df: pd.DataFrame
    raw_data_df: pd.DataFrame
    clean_data_df: pd.DataFrame
    scenarios_df: pd.DataFrame
    machines: list[str]
