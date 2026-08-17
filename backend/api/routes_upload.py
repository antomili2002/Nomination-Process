from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.api.schemas import MetricInfo, ScenarioInfoRow, UploadResponse
from backend.core.exceptions import (
    InvalidUploadError,
    InvalidWorkbookError,
    ScenarioExtractionError,
)
from backend.domain.workbook import UploadedWorkbook
from backend.services import upload_service

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
def upload_workbook(file: UploadFile = File(...)):
    """Receive an Excel workbook, extract scenario metadata, and return it."""
    try:
        result = upload_service.process_upload(file)
    except InvalidUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ScenarioExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _to_response(result)


def _to_response(upload: UploadedWorkbook) -> UploadResponse:
    return UploadResponse(
        upload_id=upload.upload_id,
        file_name=upload.file_name,
        scenarios=[ScenarioInfoRow(**vars(row)) for row in upload.scenarios],
        machines=upload.machines,
        available_metrics=[
            MetricInfo(
                key=m.key,
                label=m.label,
                column=m.column,
                category=m.category,
                default_selected=m.default_selected,
            )
            for m in upload.available_metrics
        ],
    )
