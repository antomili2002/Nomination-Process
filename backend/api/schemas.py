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
