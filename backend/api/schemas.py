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


class UploadResponse(BaseModel):
    upload_id: str
    file_name: str
    scenarios: list[ScenarioInfoRow]
    machines: list[str]


class ReportGenerationRequest(BaseModel):
    upload_id: str
    iv_chain: list[int] = Field(..., min_length=2)
    ev_chain: list[int] = Field(..., min_length=2)
    selected_machines: Optional[list[str]] = None


class ReportGenerationResponse(BaseModel):
    report_id: str
    download_url: str


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
