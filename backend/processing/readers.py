from pathlib import Path

import pandas as pd

from backend.core.exceptions import InvalidWorkbookError

REQUIRED_SHEETS = {"Info", "Data"}
_OLE_COMPOUND_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ENCRYPTED_PACKAGE_MARKER = "EncryptedPackage".encode("utf-16-le")


def _workbook_engine(path: Path) -> str:
    """Select an Excel reader from the file signature, not its extension."""
    with path.open("rb") as workbook_file:
        signature = workbook_file.read(len(_OLE_COMPOUND_SIGNATURE))
    return "calamine" if signature == _OLE_COMPOUND_SIGNATURE else "openpyxl"


def _is_password_protected_workbook(path: Path) -> bool:
    """Detect the encrypted OOXML stream within an OLE Compound File."""
    trailing_bytes = b""
    with path.open("rb") as workbook_file:
        while chunk := workbook_file.read(64 * 1024):
            data = trailing_bytes + chunk
            if _ENCRYPTED_PACKAGE_MARKER in data:
                return True
            trailing_bytes = data[-(len(_ENCRYPTED_PACKAGE_MARKER) - 1):]
    return False


def read_workbook_sheets(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open *path* and return ``(info_df, data_df)`` with no parsing applied.

    The ``pd.ExcelFile`` object is opened with a context manager so the
    underlying file handle is released immediately after parsing both sheets.
    On Windows this is critical: without it the OS keeps a write lock on the
    file, preventing ``shutil.rmtree`` from cleaning up the temp directory.
    """
    try:
        if _is_password_protected_workbook(path):
            raise InvalidWorkbookError(
                "Password-protected workbooks are not supported. Remove the Excel "
                "password and save the workbook before uploading it."
            )
        with pd.ExcelFile(path, engine=_workbook_engine(path)) as xl:
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
