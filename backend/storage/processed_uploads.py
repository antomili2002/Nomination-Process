from __future__ import annotations

import json
from pathlib import Path

from backend.domain.workbook import WorkbookData

_INFO_FILE = "info.pkl"
_RAW_DATA_FILE = "raw_data.pkl"
_CLEAN_DATA_FILE = "clean_data.pkl"
_SCENARIOS_FILE = "scenarios.pkl"
_MACHINES_FILE = "machines.json"
_PORTFOLIO_COUNTRY_FILE = "portfolio_country.json"


def save_workbook_data(upload_dir: Path, data: WorkbookData) -> None:
    """Persist parsed workbook artifacts next to the uploaded workbook."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    data.info_df.to_pickle(upload_dir / _INFO_FILE)
    data.raw_data_df.to_pickle(upload_dir / _RAW_DATA_FILE)
    data.clean_data_df.to_pickle(upload_dir / _CLEAN_DATA_FILE)
    data.scenarios_df.to_pickle(upload_dir / _SCENARIOS_FILE)
    (upload_dir / _MACHINES_FILE).write_text(
        json.dumps(data.machines),
        encoding="utf-8",
    )
    (upload_dir / _PORTFOLIO_COUNTRY_FILE).write_text(
        json.dumps(data.portfolio_country),
        encoding="utf-8",
    )


def load_workbook_data(upload_dir: Path) -> WorkbookData:
    """Load parsed workbook artifacts for a previously uploaded workbook."""
    try:
        info_df = _read_pickle(upload_dir / _INFO_FILE)
        raw_data_df = _read_pickle(upload_dir / _RAW_DATA_FILE)
        clean_data_df = _read_pickle(upload_dir / _CLEAN_DATA_FILE)
        scenarios_df = _read_pickle(upload_dir / _SCENARIOS_FILE)
        machines = _read_machines(upload_dir / _MACHINES_FILE)
        portfolio_country = _read_portfolio_country(upload_dir / _PORTFOLIO_COUNTRY_FILE)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise FileNotFoundError(
            f"Processed upload artifacts are missing or unreadable in {upload_dir}"
        ) from exc

    return WorkbookData(
        info_df=info_df,
        raw_data_df=raw_data_df,
        clean_data_df=clean_data_df,
        scenarios_df=scenarios_df,
        machines=machines,
        portfolio_country=portfolio_country,
    )


def _read_pickle(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing processed upload artifact: {path}")
    import pandas as pd

    return pd.read_pickle(path)


def _read_machines(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing processed upload artifact: {path}")
    text = path.read_text(encoding="utf-8")
    if not text:
        return []
    return list(json.loads(text))


def _read_portfolio_country(path: Path) -> str:
    """Read the persisted country, defaulting legacy uploads to the UK layout."""
    if not path.exists():
        return "UK"
    value = json.loads(path.read_text(encoding="utf-8"))
    return str(value).strip().upper() or "UK"
