"""Write the downloadable Excel report.

Styling applied explicitly matching ground-truth exports.
- Font: Aptos Narrow, 11pt.
- Bold/Fills for Pivot tables.
- Number formats for floats.
- Gridlines removed, specific blue colors and bottom borders added.
"""
from __future__ import annotations

import io
from typing import Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

_FONT_DEFAULT = Font(name="Aptos Narrow", size=11)
_FONT_BOLD = Font(name="Aptos Narrow", size=11, bold=True)

_COLOR_BLUE = "C0E6F5"
_FILL_BLUE = PatternFill(start_color=_COLOR_BLUE, fill_type="solid")

_BORDER_BOTTOM_BLUE = Border(bottom=Side(style="medium", color=_COLOR_BLUE))
_BORDER_TOP_BLUE = Border(top=Side(style="medium", color=_COLOR_BLUE))

_NUM_FMT = "#,##0"
_ALL_MONTHS = list(range(1, 13))  # 1..12


def write_report(
    report_data: dict,
    info_df: pd.DataFrame,
    data_df: pd.DataFrame,
) -> bytes:
    wb = Workbook()
    del wb["Sheet"]

    _write_monthly_sheet(wb, "EV_month", report_data["ev_monthly"], "EXTRINSIC_VALUE",      "EV")
    _write_delta_sheet  (wb, "EV_sheet", report_data["ev_deltas"],  "EXTRINSIC_VALUE",      "EV")
    _write_monthly_sheet(wb, "IV_month", report_data["iv_monthly"], "INTRINSIC_VALUE__CUR", "IV")
    _write_delta_sheet  (wb, "IV_sheet", report_data["iv_deltas"],  "INTRINSIC_VALUE__CUR", "IV")
    _write_monthly_sheet(wb, "PP_month", report_data["pp_monthly"], "POWER_POS__GWH",       "IV")
    _write_delta_sheet  (wb, "PP_sheet", report_data["pp_deltas"],  "POWER_POS__GWH",       "IV")

    _df_to_sheet(wb, "Info", info_df, write_header=False)
    _df_to_sheet(wb, "Data", data_df, write_header=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _w(ws, row: int, col: int, value, font=_FONT_DEFAULT, fill=None, indent=0, num_fmt=None, border=None) -> None:
    c = ws.cell(row=row, column=col, value=value)
    c.font = font
    if fill is not None:
        c.fill = fill
    if indent > 0:
        c.alignment = Alignment(indent=indent)
    if num_fmt is not None:
        c.number_format = num_fmt
    if border is not None:
        c.border = border


def _month_values(data_months: list[int], values: list[float]) -> list[Optional[float]]:
    lookup = dict(zip(data_months, values))
    return [lookup.get(m) for m in _ALL_MONTHS]


def _write_monthly_sheet(
    wb: Workbook,
    sheet_name: str,
    pivot_tables: list[dict],
    metric_col: str,
    output_type: str,
) -> None:
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False

    ws.column_dimensions["A"].width = 35
    for col_idx in range(2, 15):
        ws.column_dimensions[get_column_letter(col_idx)].width = 17

    _w(ws, 1, 1, "OUTPUT_TYPE", fill=_FILL_BLUE);   _w(ws, 1, 2, output_type, fill=_FILL_BLUE)
    _w(ws, 2, 1, "MACHINE_NAME", fill=_FILL_BLUE);  _w(ws, 2, 2, "(All)", fill=_FILL_BLUE)

    _w(ws, 4, 1, f"Sum of {metric_col}", font=_FONT_BOLD, fill=_FILL_BLUE)
    _w(ws, 4, 2, "Column Labels", font=_FONT_BOLD, fill=_FILL_BLUE)
    # Fill remaining row 4 items
    for c in range(3, 15):
        _w(ws, 4, c, None, fill=_FILL_BLUE)

    _w(ws, 5, 1, "Row Labels", font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_BOTTOM_BLUE)
    for i, m in enumerate(_ALL_MONTHS):
        _w(ws, 5, i + 2, m, font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_BOTTOM_BLUE)
    _w(ws, 5, 14, "Grand Total", font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_BOTTOM_BLUE)

    row_num = 6
    all_month_totals = [0.0] * 12
    has_data = [False] * 12

    for pt in pivot_tables:
        months_in_data: list[int] = pt["months"]
        pt_rows: list[dict] = pt["rows"]

        sc_agg = [sum(r["values"][i] for r in pt_rows) for i in range(len(months_in_data))]
        sc_vals = _month_values(months_in_data, sc_agg)
        sc_grand = sum(v for v in sc_vals if v is not None)

        # Scenario header
        _w(ws, row_num, 1, str(pt["title"]), font=_FONT_BOLD, border=_BORDER_BOTTOM_BLUE)
        for i, v in enumerate(sc_vals):
            # Apply border to all timeline cells under scenario row
            _w(ws, row_num, i + 2, v, font=_FONT_BOLD, num_fmt=_NUM_FMT, border=_BORDER_BOTTOM_BLUE)
            if v is not None:
                all_month_totals[i] += v
                has_data[i] = True
        _w(ws, row_num, 14, sc_grand, font=_FONT_BOLD, num_fmt=_NUM_FMT, border=_BORDER_BOTTOM_BLUE)
        row_num += 1

        years: dict[int, list[dict]] = {}
        for r in pt_rows:
            years.setdefault(r["year"], []).append(r)

        for year in sorted(years):
            yr_rows = years[year]
            yr_agg = [sum(r["values"][i] for r in yr_rows) for i in range(len(months_in_data))]
            yr_vals = _month_values(months_in_data, yr_agg)
            yr_grand = sum(v for v in yr_vals if v is not None)

            _w(ws, row_num, 1, str(year), font=_FONT_BOLD, indent=1)
            for i, v in enumerate(yr_vals):
                if v is not None:
                    _w(ws, row_num, i + 2, v, font=_FONT_BOLD, num_fmt=_NUM_FMT)
            _w(ws, row_num, 14, yr_grand, font=_FONT_BOLD, num_fmt=_NUM_FMT)
            row_num += 1

            for r in yr_rows:
                t_vals = _month_values(months_in_data, r["values"])
                t_grand = sum(v for v in t_vals if v is not None)
                _w(ws, row_num, 1, r["tariff"], indent=2)
                for i, v in enumerate(t_vals):
                    if v is not None:
                        _w(ws, row_num, i + 2, v, num_fmt=_NUM_FMT)
                _w(ws, row_num, 14, t_grand, num_fmt=_NUM_FMT)
                row_num += 1

    grand_total = sum(all_month_totals)
    _w(ws, row_num, 1, "Grand Total", font=_FONT_BOLD, fill=_FILL_BLUE)
    for i, v in enumerate(all_month_totals):
        if has_data[i]:
            _w(ws, row_num, i + 2, v, font=_FONT_BOLD, fill=_FILL_BLUE, num_fmt=_NUM_FMT)
        else:
            _w(ws, row_num, i + 2, None, font=_FONT_BOLD, fill=_FILL_BLUE)
    _w(ws, row_num, 14, grand_total, font=_FONT_BOLD, fill=_FILL_BLUE, num_fmt=_NUM_FMT)


def _write_delta_sheet(
    wb: Workbook,
    sheet_name: str,
    delta_tables: list[dict],
    metric_col: str,
    output_type: str,
) -> None:
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 25
    ws.column_dimensions["C"].width = 25
    ws.column_dimensions["D"].width = 25

    _w(ws, 1, 1, "OUTPUT_TYPE", fill=_FILL_BLUE);   _w(ws, 1, 2, output_type, fill=_FILL_BLUE)
    _w(ws, 2, 1, "MACHINE_NAME", fill=_FILL_BLUE);  _w(ws, 2, 2, "(All)", fill=_FILL_BLUE)

    row_num = 4

    for dt in delta_tables:
        right_name: str   = dt["right_name"]
        left_name:  str   = dt["left_name"]
        right_total: float = dt["right_total"]
        left_total:  float = dt["left_total"]
        delta_total: float = dt["delta_total"]
        dt_rows: list[dict] = dt["rows"]

        _w(ws, row_num, 1, "Row Labels", font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_BOTTOM_BLUE)
        _w(ws, row_num, 2, left_name, font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_BOTTOM_BLUE)
        _w(ws, row_num, 3, right_name, font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_BOTTOM_BLUE)
        _w(ws, row_num, 4, f"Dif of {metric_col}", font=_FONT_BOLD, fill=_FILL_BLUE)
        row_num += 1

        for r in dt_rows:
            _w(ws, row_num, 1, str(r["year"]), indent=1)
            _w(ws, row_num, 2, r["left_value"], num_fmt=_NUM_FMT)
            _w(ws, row_num, 3, r["right_value"], num_fmt=_NUM_FMT)
            _w(ws, row_num, 4, r["delta"], num_fmt=_NUM_FMT)
            row_num += 1

        # Add Grand Total per pair
        _w(ws, row_num, 1, "Grand Total", font=_FONT_BOLD, fill=_FILL_BLUE, border=_BORDER_TOP_BLUE)
        _w(ws, row_num, 2, left_total, font=_FONT_BOLD, fill=_FILL_BLUE, num_fmt=_NUM_FMT, border=_BORDER_TOP_BLUE)
        _w(ws, row_num, 3, right_total, font=_FONT_BOLD, fill=_FILL_BLUE, num_fmt=_NUM_FMT, border=_BORDER_TOP_BLUE)
        _w(ws, row_num, 4, delta_total, font=_FONT_BOLD, fill=_FILL_BLUE, num_fmt=_NUM_FMT, border=_BORDER_TOP_BLUE)
        row_num += 2


def _safe(v) -> object:
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def _df_to_sheet(
    wb: Workbook,
    sheet_name: str,
    df: pd.DataFrame,
    write_header: bool,
) -> None:
    ws = wb.create_sheet(sheet_name)
    if write_header:
        for col_idx, col_name in enumerate(df.columns, start=1):
            _w(ws, 1, col_idx, str(col_name))
        start_row = 2
    else:
        start_row = 1

    for row_idx, row_vals in enumerate(df.itertuples(index=False, name=None), start=start_row):
        for col_idx, val in enumerate(row_vals, start=1):
            _w(ws, row_idx, col_idx, _safe(val))
