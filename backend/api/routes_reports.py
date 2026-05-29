from fastapi import APIRouter, HTTPException

from backend.api.schemas import ChainPreviewRequest, ChainPreviewResponse, DeltaPairInfo
from backend.core.exceptions import InvalidChainError, InvalidWorkbookError, ScenarioExtractionError
from backend.processing.chain_builder import build_delta_pairs, validate_chain
from backend.processing.readers import read_workbook_sheets
from backend.processing.scenario_extraction import extract_scenarios
from backend.storage.temp_files import get_upload_path

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/preview-chain", response_model=ChainPreviewResponse)
def preview_chain(body: ChainPreviewRequest):
    """Validate IV/EV chains against the uploaded workbook and return the
    delta pairs that would be computed when generating the report.

    Use this to confirm the chain order before calling /reports/generate.
    """
    path = get_upload_path(body.upload_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Upload not found.")

    try:
        info_df, _ = read_workbook_sheets(path)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        scenario_df = extract_scenarios(info_df)
    except ScenarioExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    index_to_name: dict[int, str] = dict(
        zip(scenario_df["index"].tolist(), scenario_df["scenario_name"].tolist())
    )
    available = set(index_to_name)

    try:
        validate_chain(body.iv_chain, available)
        validate_chain(body.ev_chain, available)
    except InvalidChainError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    iv_pairs = build_delta_pairs(body.iv_chain, index_to_name)
    ev_pairs = build_delta_pairs(body.ev_chain, index_to_name)

    return ChainPreviewResponse(
        iv_pairs=[DeltaPairInfo(**vars(p)) for p in iv_pairs],
        ev_pairs=[DeltaPairInfo(**vars(p)) for p in ev_pairs],
    )
