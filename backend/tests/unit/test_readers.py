"""Unit tests for backend/processing/readers.py"""
import io
from pathlib import Path

import openpyxl
import pytest

from backend.core.exceptions import InvalidWorkbookError
from backend.processing.readers import _workbook_engine, read_workbook_sheets


_FIXTURE_DIR = Path("backend/tmp/test_fixtures")


def _fixture_path(name: str) -> Path:
    _FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    return _FIXTURE_DIR / name


def _workbook_with_sheets(*names: str) -> bytes:
    wb = openpyxl.Workbook()
    wb.active.title = names[0]
    for name in names[1:]:
        wb.create_sheet(name)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_reads_info_and_data_sheets(sample_workbook_path):
    info_df, data_df = read_workbook_sheets(sample_workbook_path)
    assert info_df is not None
    assert data_df is not None


def test_info_is_read_without_header(sample_workbook_path):
    info_df, _ = read_workbook_sheets(sample_workbook_path)
    # With header=None columns are integers 0, 1, 2 …
    assert info_df.columns[0] == 0


def test_data_has_string_column_names(sample_workbook_path):
    _, data_df = read_workbook_sheets(sample_workbook_path)
    assert "SCENARIO_ID" in data_df.columns


def test_raises_on_missing_data_sheet():
    path = _fixture_path("no_data.xlsx")
    path.write_bytes(_workbook_with_sheets("Info", "OtherSheet"))
    with pytest.raises(InvalidWorkbookError, match="Missing required sheets"):
        read_workbook_sheets(path)


def test_raises_on_missing_info_sheet():
    path = _fixture_path("no_info.xlsx")
    path.write_bytes(_workbook_with_sheets("Data", "OtherSheet"))
    with pytest.raises(InvalidWorkbookError, match="Missing required sheets"):
        read_workbook_sheets(path)


def test_raises_on_corrupt_file():
    path = _fixture_path("bad.xlsx")
    path.write_bytes(b"this is not a valid xlsx file")
    with pytest.raises(InvalidWorkbookError, match="Cannot open workbook"):
        read_workbook_sheets(path)


def test_routes_ole_compound_workbook_to_calamine_reader():
    path = _fixture_path("legacy_dexter.xlsx")
    path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"legacy workbook")

    assert _workbook_engine(path) == "calamine"


def test_raises_actionable_error_for_password_encrypted_workbook():
    path = _fixture_path("encrypted_dexter.xlsx")
    path.write_bytes(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        + "EncryptedPackage".encode("utf-16-le")
    )

    with pytest.raises(InvalidWorkbookError, match="Password-protected workbooks"):
        read_workbook_sheets(path)
