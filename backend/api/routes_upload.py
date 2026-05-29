import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.api.schemas import ScenarioInfoRow, UploadResponse
from backend.core.constants import MACHINE_NAME_COL, SCENARIO_ID_COL
from backend.core.exceptions import InvalidWorkbookError, ScenarioExtractionError
from backend.processing.cleaning import clean_data
from backend.processing.readers import read_workbook_sheets
from backend.processing.scenario_extraction import extract_scenarios
from backend.storage.temp_files import save_upload

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
def upload_workbook(file: UploadFile = File(...)):
    """Receive an Excel workbook, extract scenario metadata, and return it."""
    try:
        upload_id, path = save_upload(file)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        info_df, data_df = read_workbook_sheets(path)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        scenario_df = extract_scenarios(info_df)
    except ScenarioExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        data_df = clean_data(data_df)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    scenarios = _to_schema_rows(scenario_df)
    machines = _extract_machines(data_df)

    return UploadResponse(
        upload_id=upload_id,
        file_name=file.filename or "upload.xlsx",
        scenarios=scenarios,
        machines=machines,
    )


def _to_schema_rows(df: pd.DataFrame) -> list[ScenarioInfoRow]:
    return [
        ScenarioInfoRow(
            index=int(row["index"]),
            scenario_name=str(row["scenario_name"]),
            scenario_id=int(row["scenario_id"]),
            market_area=str(row.get("market_area", "")),
            scenario_type=str(row.get("scenario_type", "")),
            status=str(row.get("status", "")),
            role=row.get("role") or None,
        )
        for _, row in df.iterrows()
    ]


def _extract_machines(data_df: pd.DataFrame) -> list[str]:
    """Return sorted unique MACHINE_NAME values from the cleaned Data sheet."""
    if MACHINE_NAME_COL not in data_df.columns:
        return []
    return sorted(data_df[MACHINE_NAME_COL].dropna().unique().tolist())
