"""Write the downloadable Excel report with XlsxWriter.

The report is generated from scratch, so XlsxWriter is used for faster row-wise
output and reusable formats. The public interface stays compatible with the
previous writer: ``write_report(...)`` returns .xlsx bytes.
"""
from __future__ import annotations

import os
import tempfile
from typing import Optional

import pandas as pd
import xlsxwriter

_COLOR_BLUE = "#C0E6F5"
_NUM_FMT = "#,##0"
_ALL_MONTHS = list(range(1, 13))  # 1..12


def write_report(
    report_data: dict,
    info_df: pd.DataFrame,
    data_df: pd.DataFrame,
) -> bytes:
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        wb = xlsxwriter.Workbook(tmp_path, {"constant_memory": True})
        formats = _create_formats(wb)

        if report_data.get("layout", "uk") == "non_uk":
            _write_non_uk_sheets(wb, report_data["non_uk_sections"], formats)
        else:
            used_prefixes: set[str] = set()
            for metric in report_data["metrics"]:
                prefix = _unique_prefix(metric["excel_prefix"], used_prefixes)
                _write_monthly_sheet(
                    wb,
                    f"{prefix}_month",
                    metric["monthly"],
                    metric["column"],
                    metric["output_type"],
                    formats,
                )
                _write_delta_sheet(
                    wb,
                    f"{prefix}_sheet",
                    metric["deltas"],
                    metric["column"],
                    metric["output_type"],
                    formats,
                )

        _df_to_sheet(wb, "Info", info_df, write_header=False, formats=formats)
        _df_to_sheet(wb, "Data", data_df, write_header=True, formats=formats)

        wb.close()

        with open(tmp_path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _unique_prefix(prefix: str, used: set[str]) -> str:
    """Guard against Excel sheet-name collisions between dynamically discovered metrics."""
    candidate = prefix
    suffix = 2
    while candidate in used:
        candidate = f"{prefix}{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _create_formats(wb: xlsxwriter.Workbook) -> dict[str, xlsxwriter.format.Format]:
    base = {
        "font_name": "Aptos Narrow",
        "font_size": 11,
    }
    blue = {
        **base,
        "bg_color": _COLOR_BLUE,
        "pattern": 1,
    }
    bottom = {
        "bottom": 2,
        "bottom_color": _COLOR_BLUE,
    }
    top = {
        "top": 2,
        "top_color": _COLOR_BLUE,
    }

    return {
        "default": wb.add_format(base),
        "bold": wb.add_format({**base, "bold": True}),
        "indent1": wb.add_format({**base, "indent": 1}),
        "indent2": wb.add_format({**base, "indent": 2}),
        "bold_indent1": wb.add_format({**base, "bold": True, "indent": 1}),
        "bold_blue": wb.add_format({**blue, "bold": True}),
        "blue": wb.add_format(blue),
        "num": wb.add_format({**base, "num_format": _NUM_FMT}),
        "bold_num": wb.add_format({**base, "bold": True, "num_format": _NUM_FMT}),
        "bold_bottom": wb.add_format({**base, "bold": True, **bottom}),
        "bold_num_bottom": wb.add_format(
            {**base, "bold": True, "num_format": _NUM_FMT, **bottom}
        ),
        "bold_blue_bottom": wb.add_format({**blue, "bold": True, **bottom}),
        "bold_blue_num": wb.add_format(
            {**blue, "bold": True, "num_format": _NUM_FMT}
        ),
        "bold_blue_num_bottom": wb.add_format(
            {**blue, "bold": True, "num_format": _NUM_FMT, **bottom}
        ),
        "bold_blue_top": wb.add_format({**blue, "bold": True, **top}),
        "bold_blue_num_top": wb.add_format(
            {**blue, "bold": True, "num_format": _NUM_FMT, **top}
        ),
    }


def _w(ws, row: int, col: int, value, fmt=None) -> None:
    """Write a 1-based cell address for compatibility with the old writer."""
    ws.write(row - 1, col - 1, value, fmt)


def _month_values(data_months: list[int], values: list[float]) -> list[Optional[float]]:
    lookup = dict(zip(data_months, values))
    return [lookup.get(m) for m in _ALL_MONTHS]


def _write_non_uk_sheets(
    wb: xlsxwriter.Workbook,
    sections: list[dict],
    formats: dict,
) -> None:
    """Write the four non-UK views, with one table per category on each sheet."""
    for output_type, period, sheet_name in (
        ("IV", "yearly", "IV_Yearly"),
        ("IV", "monthly", "IV_Monthly"),
        ("EV", "yearly", "EV_Yearly"),
        ("EV", "monthly", "EV_Monthly"),
    ):
        ws = wb.add_worksheet(sheet_name)
        ws.hide_gridlines(2)
        ws.set_column(0, 0, 32)
        ws.set_column(1, 2, 14)
        ws.set_column(3, 20, 24)

        _w(ws, 1, 1, "OUTPUT_TYPE", formats["blue"])
        _w(ws, 1, 2, output_type, formats["blue"])
        _w(ws, 2, 1, "MACHINE_NAME", formats["blue"])
        _w(ws, 2, 2, "(All)", formats["blue"])

        row_num = 4
        matching_sections = [
            section for section in sections
            if section["output_type"] == output_type and section["period"] == period
        ]
        for section in matching_sections:
            row_num = _write_non_uk_category_table(ws, row_num, section, formats)
            row_num += 2


def _write_non_uk_category_table(
    ws: xlsxwriter.worksheet.Worksheet,
    row_num: int,
    section: dict,
    formats: dict,
) -> int:
    columns: list[dict] = section["columns"]
    rows: list[dict] = section["rows"]
    is_monthly = section["period"] == "monthly"

    _w(ws, row_num, 1, section["category"], formats["bold_blue"])
    for column_index in range(2, len(columns) + 3 + int(is_monthly)):
        _w(ws, row_num, column_index, None, formats["blue"])
    row_num += 1

    headers = ["Metric", "Year"]
    if is_monthly:
        headers.append("Month")
    headers.extend(column["label"] for column in columns)
    for column_index, header in enumerate(headers, start=1):
        _w(ws, row_num, column_index, header, formats["bold_blue_bottom"])
    row_num += 1

    totals = [0.0] * len(columns)
    for row in rows:
        _w(ws, row_num, 1, row["metric_label"], formats["indent1"])
        _w(ws, row_num, 2, row["year"], formats["num"])
        value_column = 3
        if is_monthly:
            _w(ws, row_num, 3, row["month"], formats["num"])
            value_column = 4
        for index, value in enumerate(row["values"]):
            _w(ws, row_num, value_column + index, value, formats["num"])
            totals[index] += value
        row_num += 1

    if rows:
        label_columns = 3 if is_monthly else 2
        _w(ws, row_num, 1, f"Total {section['category']}", formats["bold_blue"])
        for column_index in range(2, label_columns + 1):
            _w(ws, row_num, column_index, None, formats["blue"])
        for index, value in enumerate(totals):
            _w(ws, row_num, label_columns + 1 + index, value, formats["bold_blue_num"])
        row_num += 1

    return row_num


def _write_monthly_sheet(
    wb: xlsxwriter.Workbook,
    sheet_name: str,
    pivot_tables: list[dict],
    metric_col: str,
    output_type: str,
    formats: dict,
) -> None:
    ws = wb.add_worksheet(sheet_name)
    ws.hide_gridlines(2)

    ws.set_column(0, 0, 35)
    ws.set_column(1, 13, 17)

    _w(ws, 1, 1, "OUTPUT_TYPE", formats["blue"])
    _w(ws, 1, 2, output_type, formats["blue"])
    _w(ws, 2, 1, "MACHINE_NAME", formats["blue"])
    _w(ws, 2, 2, "(All)", formats["blue"])

    _w(ws, 4, 1, f"Sum of {metric_col}", formats["bold_blue"])
    _w(ws, 4, 2, "Column Labels", formats["bold_blue"])
    for c in range(3, 15):
        _w(ws, 4, c, None, formats["blue"])

    _w(ws, 5, 1, "Row Labels", formats["bold_blue_bottom"])
    for i, month in enumerate(_ALL_MONTHS):
        _w(ws, 5, i + 2, month, formats["bold_blue_bottom"])
    _w(ws, 5, 14, "Grand Total", formats["bold_blue_bottom"])

    row_num = 6
    all_month_totals = [0.0] * 12
    has_data = [False] * 12

    for pt in pivot_tables:
        months_in_data: list[int] = pt["months"]
        pt_rows: list[dict] = pt["rows"]

        sc_agg = [sum(r["values"][i] for r in pt_rows) for i in range(len(months_in_data))]
        sc_vals = _month_values(months_in_data, sc_agg)
        sc_grand = sum(v for v in sc_vals if v is not None)

        _w(ws, row_num, 1, str(pt["title"]), formats["bold_bottom"])
        for i, value in enumerate(sc_vals):
            _w(ws, row_num, i + 2, value, formats["bold_num_bottom"])
            if value is not None:
                all_month_totals[i] += value
                has_data[i] = True
        _w(ws, row_num, 14, sc_grand, formats["bold_num_bottom"])
        row_num += 1

        years: dict[int, list[dict]] = {}
        for row in pt_rows:
            years.setdefault(row["year"], []).append(row)

        for year in sorted(years):
            yr_rows = years[year]
            yr_agg = [sum(r["values"][i] for r in yr_rows) for i in range(len(months_in_data))]
            yr_vals = _month_values(months_in_data, yr_agg)
            yr_grand = sum(v for v in yr_vals if v is not None)

            _w(ws, row_num, 1, str(year), formats["bold_indent1"])
            for i, value in enumerate(yr_vals):
                if value is not None:
                    _w(ws, row_num, i + 2, value, formats["bold_num"])
            _w(ws, row_num, 14, yr_grand, formats["bold_num"])
            row_num += 1

            for row in yr_rows:
                tariff_vals = _month_values(months_in_data, row["values"])
                tariff_grand = sum(v for v in tariff_vals if v is not None)
                _w(ws, row_num, 1, row["tariff"], formats["indent2"])
                for i, value in enumerate(tariff_vals):
                    if value is not None:
                        _w(ws, row_num, i + 2, value, formats["num"])
                _w(ws, row_num, 14, tariff_grand, formats["num"])
                row_num += 1

    grand_total = sum(all_month_totals)
    _w(ws, row_num, 1, "Grand Total", formats["bold_blue"])
    for i, value in enumerate(all_month_totals):
        if has_data[i]:
            _w(ws, row_num, i + 2, value, formats["bold_blue_num"])
        else:
            _w(ws, row_num, i + 2, None, formats["bold_blue"])
    _w(ws, row_num, 14, grand_total, formats["bold_blue_num"])


def _write_delta_sheet(
    wb: xlsxwriter.Workbook,
    sheet_name: str,
    delta_tables: list[dict],
    metric_col: str,
    output_type: str,
    formats: dict,
) -> None:
    ws = wb.add_worksheet(sheet_name)
    ws.hide_gridlines(2)

    ws.set_column(0, 0, 35)
    ws.set_column(1, 3, 25)

    _w(ws, 1, 1, "OUTPUT_TYPE", formats["blue"])
    _w(ws, 1, 2, output_type, formats["blue"])
    _w(ws, 2, 1, "MACHINE_NAME", formats["blue"])
    _w(ws, 2, 2, "(All)", formats["blue"])

    row_num = 4

    for dt in delta_tables:
        right_name: str = dt["right_name"]
        left_name: str = dt["left_name"]
        right_total: float = dt["right_total"]
        left_total: float = dt["left_total"]
        delta_total: float = dt["delta_total"]
        dt_rows: list[dict] = dt["rows"]

        _w(ws, row_num, 1, "Row Labels", formats["bold_blue_bottom"])
        _w(ws, row_num, 2, left_name, formats["bold_blue_bottom"])
        _w(ws, row_num, 3, right_name, formats["bold_blue_bottom"])
        _w(ws, row_num, 4, f"Dif of {metric_col}", formats["bold_blue"])
        row_num += 1

        for row in dt_rows:
            _w(ws, row_num, 1, str(row["year"]), formats["indent1"])
            _w(ws, row_num, 2, row["left_value"], formats["num"])
            _w(ws, row_num, 3, row["right_value"], formats["num"])
            _w(ws, row_num, 4, row["delta"], formats["num"])
            row_num += 1

        _w(ws, row_num, 1, "Grand Total", formats["bold_blue_top"])
        _w(ws, row_num, 2, left_total, formats["bold_blue_num_top"])
        _w(ws, row_num, 3, right_total, formats["bold_blue_num_top"])
        _w(ws, row_num, 4, delta_total, formats["bold_blue_num_top"])
        row_num += 2


def _df_to_sheet(
    wb: xlsxwriter.Workbook,
    sheet_name: str,
    df: pd.DataFrame,
    write_header: bool,
    formats: dict,
) -> None:
    ws = wb.add_worksheet(sheet_name)
    ws.hide_gridlines(2)

    clean_df = df.astype(object).where(pd.notna(df), None)
    row_idx = 0

    if write_header:
        ws.write_row(row_idx, 0, [str(col) for col in clean_df.columns], formats["default"])
        row_idx += 1

    for row in clean_df.itertuples(index=False, name=None):
        ws.write_row(row_idx, 0, row, formats["default"])
        row_idx += 1
