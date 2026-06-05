"""HTTP layer for report endpoints.

Each handler:
  1. Calls the appropriate ``report_service`` function.
  2. Catches domain exceptions and maps them to HTTP status codes.
  3. Converts the returned plain-Python dict to a response schema.

No business logic lives here.
"""
from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    ChainPreviewRequest,
    ChainPreviewResponse,
    DataPreviewRequest,
    DataPreviewResponse,
    DeltaPairInfo,
    GenerateReportResponse,
    MachineYearlyDeltaRow,
    MachineYearlyDeltaTable,
    PivotRow,
    PivotTable,
    ReportGenerationRequest,
    YearlyDeltaRow,
    YearlyDeltaTable,
)
from backend.core.exceptions import InvalidChainError, InvalidWorkbookError, ScenarioExtractionError
from backend.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

# Exception mapper
def _to_http(exc: Exception) -> HTTPException:
    """Map domain exceptions to the correct HTTP status codes."""
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail="Upload not found.")
    if isinstance(exc, (InvalidWorkbookError, InvalidChainError, ScenarioExtractionError)):
        return HTTPException(status_code=422, detail=str(exc))
    raise exc  # unexpected — let FastAPI's default 500 handler take over


# Schema helpers
def _to_pivot_tables(raw_list: list[dict]) -> list[PivotTable]:
    return [
        PivotTable(
            title=t["title"],
            pair_type=t.get("pair_type"),
            step_number=t.get("step_number"),
            months=t["months"],
            rows=[PivotRow(**r) for r in t["rows"]],
        )
        for t in raw_list
    ]


def _to_yearly_delta_tables(raw_list: list[dict]) -> list[YearlyDeltaTable]:
    return [
        YearlyDeltaTable(
            left_name=d["left_name"],
            right_name=d["right_name"],
            pair_type=d["pair_type"],
            step_number=d["step_number"],
            rows=[YearlyDeltaRow(**r) for r in d["rows"]],
            left_total=d["left_total"],
            right_total=d["right_total"],
            delta_total=d["delta_total"],
        )
        for d in raw_list
    ]


def _to_machine_yearly_delta_tables(raw_list: list[dict]) -> list[MachineYearlyDeltaTable]:
    return [
        MachineYearlyDeltaTable(
            left_name=d["left_name"],
            right_name=d["right_name"],
            pair_type=d["pair_type"],
            step_number=d["step_number"],
            rows=[MachineYearlyDeltaRow(**r) for r in d["rows"]],
            left_total=d["left_total"],
            right_total=d["right_total"],
            delta_total=d["delta_total"],
        )
        for d in raw_list
    ]

# Endpoints
@router.post("/preview-chain", response_model=ChainPreviewResponse)
def preview_chain(body: ChainPreviewRequest):
    """Validate IV/EV chains and return the delta pairs that would be computed."""
    try:
        result = report_service.preview_chain(body.upload_id, body.iv_chain, body.ev_chain)
    except Exception as exc:
        raise _to_http(exc)

    return ChainPreviewResponse(
        iv_pairs=[DeltaPairInfo(**vars(p)) for p in result["iv_pairs"]],
        ev_pairs=[DeltaPairInfo(**vars(p)) for p in result["ev_pairs"]],
    )


@router.post("/data-preview", response_model=DataPreviewResponse)
def data_preview(body: DataPreviewRequest):
    """Return monthly + delta pivot tables for the live frontend preview."""
    try:
        result = report_service.preview_data(
            body.upload_id, body.iv_chain, body.ev_chain, body.selected_machines
        )
    except Exception as exc:
        raise _to_http(exc)

    return DataPreviewResponse(
        available_machines=result["available_machines"],
        ev_monthly=_to_pivot_tables(result["ev_monthly"]),
        ev_deltas=_to_pivot_tables(result["ev_deltas"]),
        iv_monthly=_to_pivot_tables(result["iv_monthly"]),
        iv_deltas=_to_pivot_tables(result["iv_deltas"]),
        pp_monthly=_to_pivot_tables(result["pp_monthly"]),
    )


@router.post("/generate", response_model=GenerateReportResponse)
def generate_report(body: ReportGenerationRequest):
    """Compute all tables for the configured chains and return the report payload."""
    try:
        result = report_service.generate_report(
            body.upload_id, body.iv_chain, body.ev_chain, body.selected_machines
        )
    except Exception as exc:
        raise _to_http(exc)

    return GenerateReportResponse(
        report_id=result["report_id"],
        upload_id=result["upload_id"],
        ev_monthly=_to_pivot_tables(result["ev_monthly"]),
        ev_deltas=_to_yearly_delta_tables(result["ev_deltas"]),
        ev_machine_deltas=_to_machine_yearly_delta_tables(result["ev_machine_deltas"]),
        iv_monthly=_to_pivot_tables(result["iv_monthly"]),
        iv_deltas=_to_yearly_delta_tables(result["iv_deltas"]),
        iv_machine_deltas=_to_machine_yearly_delta_tables(result["iv_machine_deltas"]),
        pp_monthly=_to_pivot_tables(result["pp_monthly"]),
        pp_deltas=_to_yearly_delta_tables(result["pp_deltas"]),
        pp_machine_deltas=_to_machine_yearly_delta_tables(result["pp_machine_deltas"]),
    )
