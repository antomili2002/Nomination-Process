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

from backend.domain.report_metrics import REPORT_METRICS

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

        for metric in REPORT_METRICS:
            _write_monthly_sheet(
                wb,
                f"{metric.excel_prefix}_month",
                report_data[metric.monthly_field],
                metric.column,
                metric.output_type,
                formats,
            )
            _write_delta_sheet(
                wb,
                f"{metric.excel_prefix}_sheet",
                report_data[metric.deltas_field],
                metric.column,
                metric.output_type,
                formats,
            )
            _write_machine_delta_sheet(
                wb,
                f"{metric.excel_prefix}_machine_sheet",
                report_data[metric.machine_deltas_field],
                metric.column,
                metric.output_type,
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


def _write_machine_delta_sheet(
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
    ws.set_column(1, 2, 25)

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
        _w(ws, row_num, 2, f"Sum of {metric_col}", formats["bold_blue_bottom"])
        _w(ws, row_num, 3, f"Dif of {metric_col}", formats["bold_blue_bottom"])
        row_num += 1

        left_machine_totals = _machine_totals(dt_rows, "left_value")
        right_machine_totals = _machine_totals(dt_rows, "right_value")
        delta_machine_totals = _machine_totals(dt_rows, "delta")

        _w(ws, row_num, 1, left_name, formats["bold_bottom"])
        _w(ws, row_num, 2, left_total, formats["bold_num_bottom"])
        _w(ws, row_num, 3, None, formats["bold_bottom"])
        row_num += 1

        for machine_name, rows in _rows_by_machine(dt_rows).items():
            _w(ws, row_num, 1, machine_name, formats["bold_indent1"])
            _w(ws, row_num, 2, left_machine_totals[machine_name], formats["bold_num"])
            row_num += 1
            for row in rows:
                _w(ws, row_num, 1, str(row["year"]), formats["indent2"])
                _w(ws, row_num, 2, row["left_value"], formats["num"])
                row_num += 1

        _w(ws, row_num, 1, right_name, formats["bold_bottom"])
        _w(ws, row_num, 2, right_total, formats["bold_num_bottom"])
        _w(ws, row_num, 3, delta_total, formats["bold_num_bottom"])
        row_num += 1

        for machine_name, rows in _rows_by_machine(dt_rows).items():
            _w(ws, row_num, 1, machine_name, formats["bold_indent1"])
            _w(ws, row_num, 2, right_machine_totals[machine_name], formats["bold_num"])
            _w(ws, row_num, 3, delta_machine_totals[machine_name], formats["bold_num"])
            row_num += 1
            for row in rows:
                _w(ws, row_num, 1, str(row["year"]), formats["indent2"])
                _w(ws, row_num, 2, row["right_value"], formats["num"])
                _w(ws, row_num, 3, row["delta"], formats["num"])
                row_num += 1

        _w(ws, row_num, 1, "Grand Total", formats["bold_blue_top"])
        _w(ws, row_num, 2, left_total + right_total, formats["bold_blue_num_top"])
        _w(ws, row_num, 3, None, formats["bold_blue_top"])
        row_num += 2


def _rows_by_machine(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda r: (str(r["machine_name"]), int(r["year"]))):
        grouped.setdefault(str(row["machine_name"]), []).append(row)
    return grouped


def _machine_totals(rows: list[dict], value_key: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in rows:
        machine_name = str(row["machine_name"])
        totals[machine_name] = totals.get(machine_name, 0.0) + float(row[value_key])
    return totals


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
