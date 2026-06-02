from pathlib import Path

import pandas as pd

from backend.core.exceptions import InvalidWorkbookError

REQUIRED_SHEETS = {"Info", "Data"}


def read_workbook_sheets(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open *path* and return ``(info_df, data_df)`` with no parsing applied.

    The ``pd.ExcelFile`` object is opened with a context manager so the
    underlying file handle is released immediately after parsing both sheets.
    On Windows this is critical: without it the OS keeps a write lock on the
    file, preventing ``shutil.rmtree`` from cleaning up the temp directory.
    """
    try:
        with pd.ExcelFile(path, engine="openpyxl") as xl:
            missing = REQUIRED_SHEETS - set(xl.sheet_names)
            if missing:
                raise InvalidWorkbookError(f"Missing required sheets: {sorted(missing)}")

            # Info is read without a header because the real header row varies
            info_df = xl.parse("Info", header=None)
            data_df = xl.parse("Data")
    except InvalidWorkbookError:
        raise
    except Exception as exc:
        raise InvalidWorkbookError(f"Cannot open workbook: {exc}") from exc

    return info_df, data_df
