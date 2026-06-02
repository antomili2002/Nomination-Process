from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    ChainPreviewRequest,
    ChainPreviewResponse,
    DataPreviewRequest,
    DataPreviewResponse,
    DeltaPairInfo,
    GenerateReportResponse,
    PivotRow,
    PivotTable,
    ReportGenerationRequest,
)
from backend.core.constants import EV_COL, IV_COL, MACHINE_NAME_COL, POWER_POS_COL
from backend.core.exceptions import InvalidChainError, InvalidWorkbookError, ScenarioExtractionError
from backend.processing.chain_builder import build_delta_pairs, validate_chain
from backend.processing.cleaning import clean_data
from backend.processing.delta_output import compute_delta
from backend.processing.monthly_output import aggregate_monthly
from backend.processing.pivot import to_pivot_table
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


@router.post("/data-preview", response_model=DataPreviewResponse)
def data_preview(body: DataPreviewRequest):
    """Compute and return all monthly + delta pivot tables for the given chains.

    The response is consumed by the frontend to render interactive pivot tables
    with a machine-name slicer — identical in structure to the ground-truth Excel.

    Machine handling:
      selected_machines=null  → sums over all machines (Excel default)
      selected_machines=[...] → filters to those machines first
    """
    path = get_upload_path(body.upload_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Upload not found.")

    try:
        info_df, data_df = read_workbook_sheets(path)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        scenario_df = extract_scenarios(info_df)
    except ScenarioExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    data_df = clean_data(data_df)

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
    machines: list[str] = sorted(data_df[MACHINE_NAME_COL].dropna().unique().tolist())
    sel = body.selected_machines

    def _agg(scenario_names: list[str], metric: str):
        return aggregate_monthly(data_df, scenario_names, metric, selected_machines=sel)

    def _delta_table(left_name: str, right_name: str, metric: str, pair_type: str, step_number) -> PivotTable:
        left_df = _agg([left_name], metric)
        right_df = _agg([right_name], metric)
        delta_df = compute_delta(left_df, right_df, metric, left_name, right_name)
        raw = to_pivot_table(delta_df, metric)
        return PivotTable(
            title=f"{left_name} → {right_name}",
            pair_type=pair_type,
            step_number=step_number,
            months=raw["months"],
            rows=[PivotRow(**r) for r in raw["rows"]],
        )

    def _monthly_tables(chain_indices: list[int], metric: str) -> list[PivotTable]:
        base_name  = index_to_name[chain_indices[0]]
        final_name = index_to_name[chain_indices[-1]]
        tables = []
        for name in [base_name, final_name]:
            agg = _agg([name], metric)
            raw = to_pivot_table(agg, metric)
            tables.append(PivotTable(
                title=name,
                months=raw["months"],
                rows=[PivotRow(**r) for r in raw["rows"]],
            ))
        return tables

    def _delta_tables(pairs, metric: str) -> list[PivotTable]:
        return [
            _delta_table(p.left_name, p.right_name, metric, p.pair_type, p.step_number)
            for p in pairs
        ]

    return DataPreviewResponse(
        available_machines=machines,
        ev_monthly=_monthly_tables(body.ev_chain, EV_COL),
        ev_deltas=_delta_tables(ev_pairs, EV_COL),
        iv_monthly=_monthly_tables(body.iv_chain, IV_COL),
        iv_deltas=_delta_tables(iv_pairs, IV_COL),
        pp_monthly=_monthly_tables(body.iv_chain, POWER_POS_COL),
    )


@router.post("/generate", response_model=GenerateReportResponse)
def generate_report(body: ReportGenerationRequest):
    """Compute all monthly and delta pivot tables for the configured chains.

    Returns a structured payload consumed by the ResultPage for in-browser
    inspection.  The report_id can later be used to download the Excel file.
    """
    import uuid as _uuid

    path = get_upload_path(body.upload_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Upload not found.")

    try:
        info_df, data_df = read_workbook_sheets(path)
    except InvalidWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        scenario_df = extract_scenarios(info_df)
    except ScenarioExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    data_df = clean_data(data_df)

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
    sel = body.selected_machines

    def _agg(scenario_names: list[str], metric: str):
        return aggregate_monthly(data_df, scenario_names, metric, selected_machines=sel)

    def _make_pivot(left_name: str, right_name: str, metric: str, pair_type: str, step_number) -> PivotTable:
        left_df  = _agg([left_name], metric)
        right_df = _agg([right_name], metric)
        delta_df = compute_delta(left_df, right_df, metric, left_name, right_name)
        raw = to_pivot_table(delta_df, metric)
        return PivotTable(
            title=f"{left_name} → {right_name}",
            pair_type=pair_type,
            step_number=step_number,
            months=raw["months"],
            rows=[PivotRow(**r) for r in raw["rows"]],
        )

    def _monthly(chain_indices: list[int], metric: str) -> list[PivotTable]:
        tables = []
        for idx in [chain_indices[0], chain_indices[-1]]:
            name = index_to_name[idx]
            raw  = to_pivot_table(_agg([name], metric), metric)
            tables.append(PivotTable(
                title=name, months=raw["months"],
                rows=[PivotRow(**r) for r in raw["rows"]],
            ))
        return tables

    def _deltas(pairs, metric: str) -> list[PivotTable]:
        return [_make_pivot(p.left_name, p.right_name, metric, p.pair_type, p.step_number) for p in pairs]

    report_id = str(_uuid.uuid4())

    return GenerateReportResponse(
        report_id=report_id,
        ev_monthly=_monthly(body.ev_chain, EV_COL),
        ev_deltas=_deltas(ev_pairs, EV_COL),
        iv_monthly=_monthly(body.iv_chain, IV_COL),
        iv_deltas=_deltas(iv_pairs, IV_COL),
        pp_monthly=_monthly(body.iv_chain, POWER_POS_COL),
        pp_deltas=_deltas(iv_pairs, POWER_POS_COL),
    )
