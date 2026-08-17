"""Unit tests for backend/excel/report_writer.py.

All tests work against the in-memory workbook produced by write_report().
No file I/O; no service-layer calls.
"""
import io

import openpyxl
import pandas as pd
import pytest
import xlsxwriter

from backend.excel import report_writer
from backend.excel.report_writer import write_report


@pytest.fixture(scope="module")
def simple_report_data() -> dict:
    """Minimal report_data matching the generate_report() dict structure.

    EV monthly  : Base_EV (500/cell) and Final_EV (1300/cell)
                  months = [5, 6], 2 tariffs (peak, offpeak), 1 year (2026)
    EV deltas   : Final_EV vs Base_EV, cumulative
                  right_total=5200, left_total=2000, delta=3200
    IV / PP     : analogous, using IV values (1000 / 1800 per cell)
    """
    ev_monthly = [
        {
            "title": "Base_EV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [500.0, 500.0]},
                {"year": 2026, "tariff": "peak",    "values": [500.0, 500.0]},
            ],
        },
        {
            "title": "Final_EV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [1300.0, 1300.0]},
                {"year": 2026, "tariff": "peak",    "values": [1300.0, 1300.0]},
            ],
        },
    ]

    ev_deltas = [
        {
            "left_name":   "Base_EV",
            "right_name":  "Final_EV",
            "pair_type":   "cumulative",
            "step_number": None,
            "rows": [
                {"year": 2026, "left_value": 2000.0, "right_value": 5200.0, "delta": 3200.0},
            ],
            "left_total":  2000.0,
            "right_total": 5200.0,
            "delta_total": 3200.0,
        }
    ]

    iv_monthly = [
        {
            "title": "Base_IV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [1000.0, 1000.0]},
                {"year": 2026, "tariff": "peak",    "values": [1000.0, 1000.0]},
            ],
        },
        {
            "title": "Final_IV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [1800.0, 1800.0]},
                {"year": 2026, "tariff": "peak",    "values": [1800.0, 1800.0]},
            ],
        },
    ]

    iv_deltas = [
        {
            "left_name":   "Base_IV",
            "right_name":  "Final_IV",
            "pair_type":   "cumulative",
            "step_number": None,
            "rows": [
                {"year": 2026, "left_value": 4000.0, "right_value": 7200.0, "delta": 3200.0},
            ],
            "left_total":  4000.0,
            "right_total": 7200.0,
            "delta_total": 3200.0,
        }
    ]

    # PP uses the same IV-style scenarios
    pp_monthly = [
        {
            "title": "Base_IV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [1000.0, 1000.0]},
                {"year": 2026, "tariff": "peak",    "values": [1000.0, 1000.0]},
            ],
        },
    ]

    pp_deltas = [
        {
            "left_name":   "Base_IV",
            "right_name":  "Final_IV",
            "pair_type":   "cumulative",
            "step_number": None,
            "rows": [
                {"year": 2026, "left_value": 4000.0, "right_value": 7200.0, "delta": 3200.0},
            ],
            "left_total":  4000.0,
            "right_total": 7200.0,
            "delta_total": 3200.0,
        }
    ]

    iv_heat_monthly = [
        {
            "title": "Base_IV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [900.0, 900.0]},
                {"year": 2026, "tariff": "peak",    "values": [900.0, 900.0]},
            ],
        },
        {
            "title": "Final_IV",
            "pair_type": None,
            "step_number": None,
            "months": [5, 6],
            "rows": [
                {"year": 2026, "tariff": "offpeak", "values": [1700.0, 1700.0]},
                {"year": 2026, "tariff": "peak",    "values": [1700.0, 1700.0]},
            ],
        },
    ]
    iv_heat_deltas = [
        {
            "left_name": "Base_IV",
            "right_name": "Final_IV",
            "pair_type": "cumulative",
            "step_number": None,
            "rows": [
                {"year": 2026, "left_value": 3600.0, "right_value": 6800.0, "delta": 3200.0},
            ],
            "left_total": 3600.0,
            "right_total": 6800.0,
            "delta_total": 3200.0,
        }
    ]

    heat_prod_monthly = [
        {**iv_heat_monthly[0], "rows": [
            {"year": 2026, "tariff": "offpeak", "values": [10.0, 10.0]},
            {"year": 2026, "tariff": "peak", "values": [10.0, 10.0]},
        ]},
        {**iv_heat_monthly[1], "rows": [
            {"year": 2026, "tariff": "offpeak", "values": [18.0, 18.0]},
            {"year": 2026, "tariff": "peak", "values": [18.0, 18.0]},
        ]},
    ]
    heat_prod_deltas = [
        {
            **iv_heat_deltas[0],
            "rows": [{"year": 2026, "left_value": 40.0, "right_value": 72.0, "delta": 32.0}],
            "left_total": 40.0,
            "right_total": 72.0,
            "delta_total": 32.0,
        }
    ]

    return {
        "report_id": "test-id",
        "upload_id": "test-upload-id",
        "metrics": [
            {
                "key": "ev", "label": "Extrinsic Value", "column": "EXTRINSIC_VALUE",
                "output_type": "EV", "excel_prefix": "EV",
                "monthly": ev_monthly, "deltas": ev_deltas,
            },
            {
                "key": "iv", "label": "Intrinsic Value", "column": "INTRINSIC_VALUE__CUR",
                "output_type": "IV", "excel_prefix": "IV",
                "monthly": iv_monthly, "deltas": iv_deltas,
            },
            {
                "key": "pp", "label": "Power Position", "column": "POWER_POS__GWH",
                "output_type": "IV", "excel_prefix": "PP",
                "monthly": pp_monthly, "deltas": pp_deltas,
            },
            {
                "key": "iv_heat", "label": "IV incl. heat costs", "column": "IV_INCL_HEAT_COSTS",
                "output_type": "IV", "excel_prefix": "IV_Heat",
                "monthly": iv_heat_monthly, "deltas": iv_heat_deltas,
            },
            {
                "key": "heat_prod", "label": "Heat Production", "column": "HEAT_PRODUCTION__GWH",
                "output_type": "IV", "excel_prefix": "Heat_Prod",
                "monthly": heat_prod_monthly, "deltas": heat_prod_deltas,
            },
        ],
    }


@pytest.fixture(scope="module")
def simple_info_df() -> pd.DataFrame:
    """Minimal Info DataFrame (header=None) — mirrors the conftest sample."""
    return pd.DataFrame([
        ["Uniper Sample", None, None],
        [None, None, None],
        ["Scenario Name", "Market Area", "Scenario Type"],
        ["Base_EV",  "UK", "EV"],
        ["Final_EV", "UK", "EV"],
    ])


@pytest.fixture(scope="module")
def simple_data_df() -> pd.DataFrame:
    """Minimal Data DataFrame with expected column names."""
    return pd.DataFrame({
        "SCENARIO_ID":          [200, 202],
        "SCENARIO_NAME":        ["Base_EV", "Final_EV"],
        "OUTPUT_TYPE":          ["EXTRINSIC_VALUE", "EXTRINSIC_VALUE"],
        "YEAR":                 [2026, 2026],
        "MONTH":                [5, 5],
        "TARIFF":               ["peak", "peak"],
        "MACHINE_NAME":         ["MACHINE_A", "MACHINE_A"],
        "POWER_POS__GWH":       [500.0, 1300.0],
        "INTRINSIC_VALUE__CUR": [500.0, 1300.0],
        "EXTRINSIC_VALUE":      [500.0, 1300.0],
        "IV_INCL_HEAT_COSTS":    [400.0, 700.0],
        "HEAT_PRODUCTION__GWH":  [10.0, 20.0],
    })


@pytest.fixture(scope="module")
def wb(simple_report_data, simple_info_df, simple_data_df):
    """Loaded openpyxl Workbook built once for the whole module."""
    raw = write_report(simple_report_data, simple_info_df, simple_data_df)
    return openpyxl.load_workbook(io.BytesIO(raw))


# Basic output checks 
def test_returns_bytes(simple_report_data, simple_info_df, simple_data_df):
    result = write_report(simple_report_data, simple_info_df, simple_data_df)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_uses_xlsxwriter_constant_memory(
    monkeypatch, simple_report_data, simple_info_df, simple_data_df
):
    seen = {}
    real_workbook = xlsxwriter.Workbook

    def spy_workbook(filename, options=None):
        seen["options"] = options or {}
        return real_workbook(filename, options)

    monkeypatch.setattr(report_writer.xlsxwriter, "Workbook", spy_workbook)

    write_report(simple_report_data, simple_info_df, simple_data_df)

    assert seen["options"]["constant_memory"] is True


def test_all_sheets_present(wb):
    names = wb.sheetnames
    for expected in ("EV_month", "EV_sheet", "IV_month", "IV_sheet",
                     "PP_month", "PP_sheet",
                     "IV_Heat_month", "IV_Heat_sheet",
                     "Heat_Prod_month", "Heat_Prod_sheet",
                     "Info", "Data"):
        assert expected in names, f"Sheet {expected!r} is missing"


def test_heat_cost_sheets_not_present(wb):
    assert "Heat_Cost_month" not in wb.sheetnames
    assert "Heat_Cost_sheet" not in wb.sheetnames


def test_output_sheets_before_info(wb):
    names = wb.sheetnames
    assert names.index("EV_month") < names.index("Info")
    assert names.index("PP_sheet") < names.index("Info")


def test_info_before_data(wb):
    names = wb.sheetnames
    assert names.index("Info") < names.index("Data")


# Font applied 
def test_font_name_on_ev_monthly(wb):
    ws = wb["EV_month"]
    assert ws.cell(1, 1).font.name == "Aptos Narrow"


def test_font_size_on_ev_monthly(wb):
    ws = wb["EV_month"]
    assert ws.cell(1, 1).font.size == 11.0


def test_bold_on_scenario_row(wb):
    """The scenario row header should be bolded as requested."""
    ws = wb["EV_month"]
    assert ws.cell(6, 1).font.bold is True


# Monthly sheet structure 
def test_ev_monthly_metadata_row1(wb):
    ws = wb["EV_month"]
    assert ws.cell(1, 1).value == "OUTPUT_TYPE"
    assert ws.cell(1, 2).value == "EV"


def test_ev_monthly_metadata_row2(wb):
    ws = wb["EV_month"]
    assert ws.cell(2, 1).value == "MACHINE_NAME"
    assert ws.cell(2, 2).value == "(All)"


def test_ev_monthly_pivot_header_row4(wb):
    ws = wb["EV_month"]
    assert ws.cell(4, 1).value == "Sum of EXTRINSIC_VALUE"
    assert ws.cell(4, 2).value == "Column Labels"


def test_ev_monthly_column_header_row5(wb):
    ws = wb["EV_month"]
    assert ws.cell(5, 1).value == "Row Labels"
    assert ws.cell(5, 2).value == 1     # month 1
    assert ws.cell(5, 13).value == 12   # month 12
    assert ws.cell(5, 14).value == "Grand Total"


def test_ev_monthly_scenario_name(wb):
    ws = wb["EV_month"]
    # Row 6 = first scenario (Base_EV)
    assert ws.cell(6, 1).value == "Base_EV"


def test_ev_monthly_scenario_month5_value(wb):
    # Base_EV month-5 aggregate = offpeak(500) + peak(500) = 1000
    ws = wb["EV_month"]
    assert ws.cell(6, 6).value == pytest.approx(1000.0)  # col 6 = month 5


def test_ev_monthly_scenario_month6_value(wb):
    ws = wb["EV_month"]
    assert ws.cell(6, 7).value == pytest.approx(1000.0)  # col 7 = month 6


def test_ev_monthly_scenario_grand_total(wb):
    # Base_EV: 1000 (month5) + 1000 (month6) = 2000
    ws = wb["EV_month"]
    assert ws.cell(6, 14).value == pytest.approx(2000.0)


def test_ev_monthly_year_row(wb):
    # Row 7 = year row (2026) under Base_EV
    ws = wb["EV_month"]
    assert ws.cell(7, 1).value == "2026"
    assert ws.cell(7, 6).value == pytest.approx(1000.0)
    assert ws.cell(7, 14).value == pytest.approx(2000.0)


def test_ev_monthly_tariff_rows(wb):
    # Rows 8–9 = tariff leaf rows under 2026 / Base_EV
    ws = wb["EV_month"]
    tariff_vals = {ws.cell(8, 1).value, ws.cell(9, 1).value}
    assert "offpeak" in tariff_vals
    assert "peak" in tariff_vals
    # Each tariff: 500 per month × 2 months = 1000 grand total
    assert ws.cell(8, 14).value == pytest.approx(1000.0)
    assert ws.cell(9, 14).value == pytest.approx(1000.0)


def test_ev_monthly_grand_total_row(wb):
    # Grand Total = Base_EV(2000) + Final_EV(5200) per column-total sums
    # month-5 total = 1000 + 2600 = 3600
    ws = wb["EV_month"]
    grand_row = None
    for row in ws.iter_rows():
        if row[0].value == "Grand Total":
            grand_row = row
            break
    assert grand_row is not None, "Grand Total row not found"
    assert grand_row[5].value == pytest.approx(3600.0)   # col 6 (0-indexed 5) = month 5
    assert grand_row[13].value == pytest.approx(7200.0)  # col 14 (0-indexed 13) = Grand Total


# Delta sheet structure 
def test_ev_sheet_metadata(wb):
    ws = wb["EV_sheet"]
    assert ws.cell(1, 1).value == "OUTPUT_TYPE"
    assert ws.cell(1, 2).value == "EV"
    assert ws.cell(2, 1).value == "MACHINE_NAME"
    assert ws.cell(2, 2).value == "(All)"


def test_ev_sheet_metadata_fill_stops_at_column_b(wb):
    ws = wb["EV_sheet"]
    assert ws.cell(1, 1).fill.fill_type == "solid"
    assert ws.cell(1, 2).fill.fill_type == "solid"
    assert ws.cell(1, 3).fill.fill_type is None
    assert ws.cell(2, 4).fill.fill_type is None


def test_ev_sheet_header(wb):
    ws = wb["EV_sheet"]
    assert ws.cell(4, 1).value == "Row Labels"
    assert ws.cell(4, 2).value == "Base_EV"
    assert ws.cell(4, 3).value == "Final_EV"
    assert ws.cell(4, 4).value == "Dif of EXTRINSIC_VALUE"


def test_ev_sheet_header_bottom_border_stops_at_last_scenario(wb):
    ws = wb["EV_sheet"]
    assert ws.cell(4, 1).border.bottom.style == "medium"
    assert ws.cell(4, 2).border.bottom.style == "medium"
    assert ws.cell(4, 3).border.bottom.style == "medium"
    assert ws.cell(4, 4).border.bottom.style is None


def test_ev_sheet_year_row(wb):
    ws = wb["EV_sheet"]
    assert ws.cell(5, 1).value == "2026"
    assert ws.cell(5, 2).value == pytest.approx(2000.0)
    assert ws.cell(5, 3).value == pytest.approx(5200.0)
    assert ws.cell(5, 4).value == pytest.approx(3200.0)


def test_ev_sheet_grand_total(wb):
    ws = wb["EV_sheet"]
    assert ws.cell(6, 1).value == "Grand Total"
    assert ws.cell(6, 2).value == pytest.approx(2000.0)
    assert ws.cell(6, 3).value == pytest.approx(5200.0)
    assert ws.cell(6, 4).value == pytest.approx(3200.0)


def test_ev_sheet_grand_total_has_top_border(wb):
    ws = wb["EV_sheet"]
    for col in range(1, 5):
        assert ws.cell(6, col).border.top.style == "medium"


# Info and Data sheets 
def test_info_sheet_first_cell(wb):
    ws = wb["Info"]
    assert ws.cell(1, 1).value == "Uniper Sample"


def test_info_sheet_scenario_name_header(wb):
    # Row 3 (0-indexed row 2 in our fixture) contains "Scenario Name"
    ws = wb["Info"]
    assert ws.cell(3, 1).value == "Scenario Name"


def test_data_sheet_column_headers(wb):
    ws = wb["Data"]
    assert ws.cell(1, 1).value == "SCENARIO_ID"
    assert ws.cell(1, 3).value == "OUTPUT_TYPE"


def test_data_sheet_first_data_row(wb):
    ws = wb["Data"]
    # Row 2 = first data row (SCENARIO_ID=200, SCENARIO_NAME=Base_EV)
    assert ws.cell(2, 1).value == 200
    assert ws.cell(2, 2).value == "Base_EV"


def test_non_uk_report_writes_consolidated_iv_ev_monthly_yearly_sheets(
    simple_info_df,
    simple_data_df,
):
    columns = [
        {"label": "Base", "kind": "scenario"},
        {"label": "Final", "kind": "scenario"},
        {"label": "Final - Base", "kind": "delta"},
    ]
    report_data = {
        "layout": "non_uk",
        "metrics": [],
        "non_uk_sections": [
            {
                "output_type": "IV",
                "period": "yearly",
                "category": "Core Value Metrics",
                "columns": columns,
                "rows": [
                    {"metric_key": "iv", "metric_label": "Intrinsic Value", "year": 2026, "values": [4000.0, 7200.0, 3200.0]},
                    {"metric_key": "pp", "metric_label": "Power Position", "year": 2026, "values": [4000.0, 7200.0, 3200.0]},
                ],
            },
            {
                "output_type": "IV",
                "period": "monthly",
                "category": "Core Value Metrics",
                "columns": columns,
                "rows": [
                    {"metric_key": "iv", "metric_label": "Intrinsic Value", "year": 2026, "month": 5, "values": [2000.0, 3600.0, 1600.0]},
                ],
            },
            {
                "output_type": "EV",
                "period": "yearly",
                "category": "Core Value Metrics",
                "columns": columns,
                "rows": [
                    {"metric_key": "ev", "metric_label": "Extrinsic Value", "year": 2026, "values": [2000.0, 5200.0, 3200.0]},
                ],
            },
            {
                "output_type": "EV",
                "period": "monthly",
                "category": "Core Value Metrics",
                "columns": columns,
                "rows": [
                    {"metric_key": "ev", "metric_label": "Extrinsic Value", "year": 2026, "month": 5, "values": [1000.0, 2600.0, 1600.0]},
                ],
            },
        ],
    }

    workbook = openpyxl.load_workbook(io.BytesIO(write_report(report_data, simple_info_df, simple_data_df)))

    assert {"IV_Yearly", "IV_Monthly", "EV_Yearly", "EV_Monthly"}.issubset(workbook.sheetnames)
    assert not any(name.endswith("_month") or name.endswith("_sheet") for name in workbook.sheetnames)
    iv_yearly = workbook["IV_Yearly"]
    assert iv_yearly.cell(4, 1).value == "Core Value Metrics"
    assert [iv_yearly.cell(5, col).value for col in range(1, 6)] == [
        "Metric", "Year", "Base", "Final", "Final - Base",
    ]
    assert iv_yearly.cell(6, 1).value == "Intrinsic Value"
    assert iv_yearly.cell(6, 3).value == pytest.approx(4000.0)
    assert iv_yearly.cell(6, 5).value == pytest.approx(3200.0)
    assert all("%" not in str(cell.value) for row in iv_yearly.iter_rows() for cell in row if cell.value)
    assert all("tariff" not in str(cell.value).lower() for row in iv_yearly.iter_rows() for cell in row if cell.value)
