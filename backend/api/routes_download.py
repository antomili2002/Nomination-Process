"""HTTP controller for the Excel download endpoint.

Single responsibility: accept the request, call the download service,
and stream the resulting workbook bytes back to the client.

No business logic lives here.
"""
import io

from fastapi import APIRouter, HTTPException, Response

from backend.api.schemas import ReportGenerationRequest
from backend.core.exceptions import InvalidChainError, InvalidWorkbookError, ScenarioExtractionError
from backend.domain.dimension_filters import DimensionFilters
from backend.services import download_service

router = APIRouter(prefix="/reports", tags=["reports"])

_XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _to_http(exc: Exception) -> HTTPException:
    """Map domain exceptions to the correct HTTP status codes."""
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail="Upload not found.")
    if isinstance(exc, (InvalidWorkbookError, InvalidChainError, ScenarioExtractionError)):
        return HTTPException(status_code=422, detail=str(exc))
    raise exc  # unexpected — let FastAPI's default 500 handler take over


@router.post("/export")
def export_report(body: ReportGenerationRequest):
    """Generate and stream the Excel report file for download."""
    try:
        dim_filters: DimensionFilters | None = None
        if body.dimension_filters:
            df = body.dimension_filters
            dim_filters = DimensionFilters(
                machine_names=df.machine_names,
                plant_names=df.plant_names,
                unit_names=df.unit_names,
                fuel_names=df.fuel_names,
            )
        dim_filters2: DimensionFilters | None = None
        if body.dimension_filters_2:
            df2 = body.dimension_filters_2
            dim_filters2 = DimensionFilters(
                machine_names=df2.machine_names,
                plant_names=df2.plant_names,
                unit_names=df2.unit_names,
                fuel_names=df2.fuel_names,
            )
        excel_bytes, filename = download_service.create_excel_report(
            body.upload_id, body.iv_chain, body.ev_chain,
            body.selected_machines, body.selected_metrics, dim_filters, dim_filters2,
        )
    except Exception as exc:
        raise _to_http(exc)

    return Response(
        content=excel_bytes,
        media_type=_XLSX_CONTENT_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(excel_bytes)),
        },
    )
