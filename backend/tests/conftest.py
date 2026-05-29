"""Shared pytest fixtures for all test suites."""
import io
from pathlib import Path

import openpyxl
import pandas as pd
import pytest


def _build_sample_workbook() -> bytes:
    """Return a .xlsx workbook bytes with Info + Data sheets.

    Info sheet
    ----------
    Row 0  : title cell ("Uniper Sample")
    Row 1  : empty
    Row 2  : header  → Scenario Name | Market Area | Scenario Type | Status | Scenario ID | Role
    Row 3  : Base_IV  | UK | IV   | Active | 100 | base
    Row 4  : Outage_IV| UK | IV   | Active | 101 | outages
    Row 5  : Final_IV | UK | IV   | Active | 102 | new
    Row 6  : Base_EV  | UK | EV   | Active | 200 | base
    Row 7  : Outage_EV| UK | EV   | Active | 201 | outages
    Row 8  : Final_EV | UK | EV   | Active | 202 | new

    Data sheet
    ----------
    3 IV scenarios × 2 months × 2 tariffs × 1 machine = 12 rows (IV)
    3 EV scenarios × 2 months × 2 tariffs × 1 machine = 12 rows (EV)
    Total: 24 rows (known deterministic values)

    EV values  Base=500, Outage=700, Final=1300  (step Δ: 200/600, cum Δ: 800)
    IV values  Base=1000, Outage=1200, Final=1800 (step Δ: 200/600, cum Δ: 800)
    """
    wb = openpyxl.Workbook()

    # Info sheet
    ws_info = wb.active
    ws_info.title = "Info"

    ws_info.append(["Uniper Sample"])          # row 1 (1-indexed)
    ws_info.append([])                         # row 2  blank
    ws_info.append([                           # row 3  header
        "Scenario Name", "Market Area", "Scenario Type",
        "Status", "Scenario ID", "Role",
    ])
    scenarios = [
        ("Base_IV",   "UK", "IV", "Active", 100, "base"),
        ("Outage_IV", "UK", "IV", "Active", 101, "outages"),
        ("Final_IV",  "UK", "IV", "Active", 102, "new"),
        ("Base_EV",   "UK", "EV", "Active", 200, "base"),
        ("Outage_EV", "UK", "EV", "Active", 201, "outages"),
        ("Final_EV",  "UK", "EV", "Active", 202, "new"),
    ]
    for s in scenarios:
        ws_info.append(list(s))

    # Data sheet
    ws_data = wb.create_sheet("Data")
    headers = [
        "SCENARIO_ID", "SCENARIO_NAME", "OUTPUT_TYPE",
        "YEAR", "MONTH", "TARIFF", "MACHINE_NAME",
        "POWER_POS__GWH", "INTRINSIC_VALUE__CUR", "EXTRINSIC_VALUE",
    ]
    ws_data.append(headers)

    # Deterministic values keyed by (scenario_name, output_type)
    ev_values = {"Base_EV": 500.0, "Outage_EV": 700.0, "Final_EV": 1300.0}
    iv_values = {"Base_IV": 1000.0, "Outage_IV": 1200.0, "Final_IV": 1800.0}

    for name, sid, otype, values in [
        ("Base_IV",   100, "INTRINSIC_VALUE", iv_values),
        ("Outage_IV", 101, "INTRINSIC_VALUE", iv_values),
        ("Final_IV",  102, "INTRINSIC_VALUE", iv_values),
        ("Base_EV",   200, "EXTRINSIC_VALUE", ev_values),
        ("Outage_EV", 201, "EXTRINSIC_VALUE", ev_values),
        ("Final_EV",  202, "EXTRINSIC_VALUE", ev_values),
    ]:
        val = values[name]
        for month in [5, 6]:
            for tariff in ["peak", "offpeak"]:
                ws_data.append([
                    sid, name, otype,
                    2026, month, tariff, "MACHINE_A",
                    val,   # POWER_POS__GWH
                    val,   # INTRINSIC_VALUE__CUR
                    val,   # EXTRINSIC_VALUE
                ])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture(scope="session")
def sample_workbook_bytes() -> bytes:
    return _build_sample_workbook()


@pytest.fixture(scope="session")
def sample_workbook_path(tmp_path_factory, sample_workbook_bytes) -> Path:
    p = tmp_path_factory.mktemp("fixtures") / "sample_input.xlsx"
    p.write_bytes(sample_workbook_bytes)
    return p


@pytest.fixture(scope="session")
def info_df(sample_workbook_path) -> pd.DataFrame:
    xl = pd.ExcelFile(sample_workbook_path, engine="openpyxl")
    return xl.parse("Info", header=None)


@pytest.fixture(scope="session")
def data_df(sample_workbook_path) -> pd.DataFrame:
    xl = pd.ExcelFile(sample_workbook_path, engine="openpyxl")
    return xl.parse("Data")
