from typing import Optional

from pydantic import BaseModel, Field


class ScenarioInfoRow(BaseModel):
    index: int
    scenario_name: str
    scenario_id: int
    market_area: str = ""
    scenario_type: str = ""
    status: str = ""
    role: Optional[str] = None


class MetricInfo(BaseModel):
    key: str
    label: str
    column: str
    category: str
    default_selected: bool


class UploadResponse(BaseModel):
    upload_id: str
    file_name: str
    scenarios: list[ScenarioInfoRow]
    machines: list[str]
    available_metrics: list[MetricInfo]


class ReportGenerationRequest(BaseModel):
    upload_id: str
    iv_chain: list[int] = Field(..., min_length=2)
    ev_chain: list[int] = Field(..., min_length=2)
    selected_machines: Optional[list[str]] = None
    selected_metrics: Optional[list[str]] = None


class DeltaPairInfo(BaseModel):
    left_index: int
    right_index: int
    left_name: str
    right_name: str
    pair_type: str              # "step" | "cumulative"
    step_number: Optional[int] = None  # 1-based for steps, None for cumulative


class ChainPreviewRequest(BaseModel):
    upload_id: str
    iv_chain: list[int] = Field(..., min_length=2)
    ev_chain: list[int] = Field(..., min_length=2)


class ChainPreviewResponse(BaseModel):
    iv_pairs: list[DeltaPairInfo]
    ev_pairs: list[DeltaPairInfo]


# Data preview — pivot tables for frontend visualisation
class PivotRow(BaseModel):
    year: int
    tariff: str
    values: list[float]          # aligned to PivotTable.months


class PivotTable(BaseModel):
    title: str                   # scenario name or "Base → Final" delta label
    pair_type: Optional[str] = None   # None for monthly, "step"|"cumulative" for deltas
    step_number: Optional[int] = None
    months: list[int]            # e.g. [5, 6]
    rows: list[PivotRow]


class DataPreviewRequest(BaseModel):
    upload_id: str
    iv_chain: list[int] = Field(..., min_length=2)
    ev_chain: list[int] = Field(..., min_length=2)
    selected_machines: Optional[list[str]] = None


class DataPreviewResponse(BaseModel):
    available_machines: list[str]
    ev_monthly: list[PivotTable]   # base + final EV scenarios
    ev_deltas:  list[PivotTable]   # all EV delta pairs (steps + cumulative)
    iv_monthly: list[PivotTable]   # base + final IV scenarios
    iv_deltas:  list[PivotTable]   # all IV delta pairs
    pp_monthly: list[PivotTable]   # power position (same IV scenarios)
    pp_deltas:  list[PivotTable]
    iv_heat_monthly: list[PivotTable]
    iv_heat_deltas:  list[PivotTable]
    heat_prod_monthly: list[PivotTable]
    heat_prod_deltas:  list[PivotTable]


class YearlyDeltaRow(BaseModel):
    year: int
    left_value: float
    right_value: float
    delta: float          # right − left


class YearlyDeltaTable(BaseModel):
    left_name:   str
    right_name:  str
    pair_type:   str                 # "step" | "cumulative"
    step_number: Optional[int] = None
    rows:        list[YearlyDeltaRow]
    left_total:  float
    right_total: float
    delta_total: float               # right_total − left_total


class MetricReportSection(BaseModel):
    key: str
    label: str
    column: str
    monthly: list[PivotTable]
    deltas:  list[YearlyDeltaTable]


class GenerateReportResponse(BaseModel):
    report_id: str
    upload_id: str
    metrics: list[MetricReportSection]
