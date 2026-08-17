from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from fastapi import UploadFile

from backend.core.constants import MACHINE_NAME_COL, UNIT_COUNTRY_COL
from backend.core.config import settings
from backend.domain.report_metrics import available_metrics
from backend.domain.workbook import ScenarioInfo, UploadedWorkbook, WorkbookData
from backend.processing.cleaning import clean_data
from backend.processing.readers import read_workbook_sheets
from backend.processing.scenario_extraction import extract_scenarios
from backend.storage.processed_uploads import save_workbook_data
from backend.storage.temp_files import save_upload


def process_upload(file: UploadFile) -> UploadedWorkbook:
    """Save an uploaded workbook and persist parsed artifacts for later use."""
    upload_id, path = save_upload(file)
    info_df, raw_data_df = read_workbook_sheets(path)
    scenarios_df, clean_data_df = _process_workbook_frames(info_df, raw_data_df)
    machines = _extract_machines(clean_data_df)
    portfolio_country = detect_portfolio_country(clean_data_df)

    save_workbook_data(
        settings.upload_dir / upload_id,
        WorkbookData(
            info_df=info_df,
            raw_data_df=raw_data_df,
            clean_data_df=clean_data_df,
            scenarios_df=scenarios_df,
            machines=machines,
            portfolio_country=portfolio_country,
        ),
    )

    return UploadedWorkbook(
        upload_id=upload_id,
        file_name=file.filename or "upload.xlsx",
        scenarios=_to_domain_scenarios(scenarios_df),
        machines=machines,
        available_metrics=list(available_metrics(clean_data_df)),
        portfolio_country=portfolio_country,
    )


def _process_workbook_frames(
    info_df: pd.DataFrame,
    raw_data_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract metadata and clean data concurrently after workbook parsing."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        scenarios_future = executor.submit(extract_scenarios, info_df)
        clean_data_future = executor.submit(clean_data, raw_data_df)
        scenarios_df = scenarios_future.result()
        clean_data_df = clean_data_future.result()
    return scenarios_df, clean_data_df


def _to_domain_scenarios(df: pd.DataFrame) -> list[ScenarioInfo]:
    return [
        ScenarioInfo(
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
    if MACHINE_NAME_COL not in data_df.columns:
        return []
    return sorted(data_df[MACHINE_NAME_COL].dropna().unique().tolist())


def detect_portfolio_country(data_df: pd.DataFrame) -> str:
    """Return the normalized portfolio country from the optional Data-sheet field."""
    if UNIT_COUNTRY_COL not in data_df.columns:
        return "UK"

    countries = data_df[UNIT_COUNTRY_COL].dropna().astype(str).str.strip()
    countries = countries[countries.str.lower().ne("nan") & countries.ne("")]
    if countries.empty:
        return "UK"
    return countries.iloc[0].upper()
