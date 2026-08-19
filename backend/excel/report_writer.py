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

from backend.domain.layout import LAYOUT_NON_UK, LAYOUT_UK

_COLOR_BLUE = "#C0E6F5"
_NUM_FMT = "#,##0"
_ALL_MONTHS = list(range(1, 13))  # 1..12


def write_report(
    report_data: dict,
    info_df: pd.DataFrame,
    data_df: pd.DataFrame,
    filtered_report_data: dict | None = None,
    filter_summary: dict[str, str] | None = None,
) -> bytes:
    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    tmp_path = tmp.name
    tmp.close()

    try:
        # Disable constant-memory mode when writing a comparison so we can
        # write filtered columns alongside original ones in the same rows.
        wb = xlsxwriter.Workbook(tmp_path, {"constant_memory": filtered_report_data is None})
        formats = _create_formats(wb)

        if report_data.get("layout", LAYOUT_UK) == LAYOUT_NON_UK:
            _write_non_uk_sheets(
                wb, report_data["non_uk_sections"], formats,
                filtered_sections=filtered_report_data["non_uk_sections"] if filtered_report_data else None,
                filter_summary=filter_summary,
            )
        else:
            _write_uk_metric_sheets(
                wb, report_data["metrics"], formats,
                filtered_metrics=filtered_report_data["metrics"] if filtered_report_data else None,
                filter_summary=filter_summary,
            )

        _df_to_sheet(wb, "Info", info_df, write_header=False, formats=formats)
        _df_to_sheet(wb, "Data", data_df, write_header=True, formats=formats)

        wb.close()

        with open(tmp_path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _write_uk_metric_sheets(
    wb: xlsxwriter.Workbook,
    metrics: list[dict],
    formats: dict,
    filtered_metrics: list[dict] | None = None,
    filter_summary: dict[str, str] | None = None,
) -> None:
    """Write one monthly + one delta sheet per metric for the UK layout."""
    used_prefixes: set[str] = set()
    for i, metric in enumerate(metrics):
        prefix = _unique_prefix(metric["excel_prefix"], used_prefixes)
        filt = filtered_metrics[i] if filtered_metrics and i < len(filtered_metrics) else None
        _write_monthly_sheet(
            wb, f"{prefix}_month",
            metric["monthly"], metric["column"], metric["output_type"], formats,
            filtered_pivot_tables=filt["monthly"] if filt else None,
            filter_summary=filter_summary,
        )
        _write_delta_sheet(
            wb, f"{prefix}_sheet",
            metric["deltas"], metric["column"], metric["output_type"], formats,
            filtered_delta_tables=filt["deltas"] if filt else None,
            filter_summary=filter_summary,
        )


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
    filtered_sections: list[dict] | None = None,
    filter_summary: dict[str, str] | None = None,
) -> None:
    """Write the four non-UK views; optionally add filtered comparison to the right."""
    for output_type, period, sheet_name in (
        ("IV", "yearly", "IV_Yearly"),
        ("IV", "monthly", "IV_Monthly"),
        ("EV", "yearly", "EV_Yearly"),
        ("EV", "monthly", "EV_Monthly"),
    ):
        ws = wb.add_worksheet(sheet_name)
        ws.hide_gridlines(2)

        matching = [
            s for s in sections
            if s["output_type"] == output_type and s["period"] == period
        ]
        matching_filtered = [
            s for s in (filtered_sections or [])
            if s["output_type"] == output_type and s["period"] == period
        ]
        has_comparison = bool(matching_filtered and filter_summary)

        # Compute column widths: Row Labels + N value columns
        orig_width = (1 + len(matching[0]["columns"])) if matching else 2
        # 2-column gap then filtered table
        filt_col_start = orig_width + 3 if has_comparison else None

        ws.set_column(0, 0, 34)
        ws.set_column(1, orig_width, 26)
        if filt_col_start:
            fc = filt_col_start - 1  # 0-indexed
            ws.set_column(fc, fc, 34)
            ws.set_column(fc + 1, fc + orig_width + 1, 26)

        _w(ws, 1, 1, "OUTPUT_TYPE", formats["blue"])
        _w(ws, 1, 2, output_type, formats["blue"])
        _w(ws, 2, 1, "MACHINE_NAME", formats["blue"])
        _w(ws, 2, 2, "(All)", formats["blue"])

        if filt_col_start:
            for row_i, (key, value) in enumerate(filter_summary.items(), start=1):  # type: ignore[union-attr]
                _w(ws, row_i, filt_col_start, key, formats["blue"])
                _w(ws, row_i, filt_col_start + 1, value, formats["blue"])

        row_num = 4
        for i, section in enumerate(matching):
            start_row = row_num
            row_num = _write_non_uk_category_table(ws, row_num, section, formats, col_start=1)
            if has_comparison and i < len(matching_filtered):
                _write_non_uk_category_table(
                    ws, start_row, matching_filtered[i], formats,
                    col_start=filt_col_start,  # type: ignore[arg-type]
                )
            row_num += 2


def _write_non_uk_category_table(
    ws: xlsxwriter.worksheet.Worksheet,
    row_num: int,
    section: dict,
    formats: dict,
    col_start: int = 1,
) -> int:
    """One category table: caption, header, metric groups, then total rows."""
    columns: list[dict] = section["columns"]
    rows: list[dict] = section["rows"]
    is_monthly = section["period"] == "monthly"
    value_count = len(columns)

    _w(ws, row_num, col_start, section["category"], formats["bold"])
    row_num += 1

    _w(ws, row_num, col_start, "Row Labels", formats["bold_blue_bottom"])
    for index, column in enumerate(columns):
        _w(ws, row_num, col_start + 1 + index, column["label"], formats["bold_blue_bottom"])
    row_num += 1

    groups, order = _group_rows_by_metric(rows)

    for metric_key in order:
        row_num = _write_non_uk_metric_group(
            ws, row_num, columns, groups[metric_key], is_monthly, formats, col_start=col_start
        )

    for metric_key in order:
        metric_rows = groups[metric_key]
        metric_col = metric_rows[0]["metric_column"]
        totals = [sum(r["values"][i] for r in metric_rows) for i in range(value_count)]
        _w(ws, row_num, col_start, f"Total Sum of {metric_col}", formats["bold_blue_top"])
        for i in range(value_count):
            _w(ws, row_num, col_start + 1 + i, totals[i], formats["bold_blue_num_top"])
        row_num += 1

    return row_num


def _write_non_uk_metric_group(
    ws: xlsxwriter.worksheet.Worksheet,
    row_num: int,
    columns: list[dict],
    metric_rows: list[dict],
    is_monthly: bool,
    formats: dict,
    col_start: int = 1,
) -> int:
    value_count = len(columns)
    metric_col = metric_rows[0]["metric_column"]

    # "Sum of <metric>" band: bold caption with a thin blue rule underneath.
    _w(ws, row_num, col_start, f"Sum of {metric_col}", formats["bold_bottom"])
    for i in range(value_count):
        _w(ws, row_num, col_start + 1 + i, None, formats["bold_bottom"])
    row_num += 1

    if not is_monthly:
        for row in metric_rows:
            _w(ws, row_num, col_start, int(row["year"]), formats["indent1"])
            for i in range(value_count):
                _w(ws, row_num, col_start + 1 + i, row["values"][i], formats["num"])
            row_num += 1
        return row_num

    # Monthly: bold year subtotal row, then indented 01.MM.YYYY month rows.
    years, year_order = _group_rows_by_year(metric_rows)
    for year in sorted(year_order):
        year_rows = years[year]
        year_totals = [sum(r["values"][i] for r in year_rows) for i in range(value_count)]
        _w(ws, row_num, col_start, int(year), formats["bold_indent1"])
        for i in range(value_count):
            _w(ws, row_num, col_start + 1 + i, year_totals[i], formats["bold_num"])
        row_num += 1

        for row in sorted(year_rows, key=lambda r: r["month"]):
            label = f"01.{int(row['month']):02d}.{int(year)}"
            _w(ws, row_num, col_start, label, formats["indent2"])
            for i in range(value_count):
                _w(ws, row_num, col_start + 1 + i, row["values"][i], formats["num"])
            row_num += 1

    return row_num


def _group_rows_by_metric(rows: list[dict]) -> tuple[dict[str, list[dict]], list[str]]:
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for row in rows:
        key = row["metric_key"]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    return groups, order


def _group_rows_by_year(rows: list[dict]) -> tuple[dict[int, list[dict]], list[int]]:
    groups: dict[int, list[dict]] = {}
    order: list[int] = []
    for row in rows:
        year = int(row["year"])
        if year not in groups:
            groups[year] = []
            order.append(year)
        groups[year].append(row)
    return groups, order


def _write_monthly_sheet(
    wb: xlsxwriter.Workbook,
    sheet_name: str,
    pivot_tables: list[dict],
    metric_col: str,
    output_type: str,
    formats: dict,
    filtered_pivot_tables: list[dict] | None = None,
    filter_summary: dict[str, str] | None = None,
) -> None:
    # Filtered table starts 2 columns after the 14-column original (col 17).
    _FILT_BASE = 17

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

    _write_monthly_body(ws, 1, pivot_tables, formats)

    if filtered_pivot_tables and filter_summary:
        ws.set_column(_FILT_BASE - 1, _FILT_BASE - 1, 35)
        ws.set_column(_FILT_BASE, _FILT_BASE + 12, 17)

        for row_i, (key, value) in enumerate(filter_summary.items(), start=1):
            _w(ws, row_i, _FILT_BASE, key, formats["blue"])
            _w(ws, row_i, _FILT_BASE + 1, value, formats["blue"])

        _w(ws, 4, _FILT_BASE, f"Sum of {metric_col}", formats["bold_blue"])
        _w(ws, 4, _FILT_BASE + 1, "Column Labels", formats["bold_blue"])
        for c in range(_FILT_BASE + 2, _FILT_BASE + 14):
            _w(ws, 4, c, None, formats["blue"])

        _w(ws, 5, _FILT_BASE, "Row Labels", formats["bold_blue_bottom"])
        for i, month in enumerate(_ALL_MONTHS):
            _w(ws, 5, _FILT_BASE + i + 1, month, formats["bold_blue_bottom"])
        _w(ws, 5, _FILT_BASE + 13, "Grand Total", formats["bold_blue_bottom"])

        _write_monthly_body(ws, _FILT_BASE, filtered_pivot_tables, formats)


def _write_monthly_body(
    ws: xlsxwriter.worksheet.Worksheet,
    col_base: int,
    pivot_tables: list[dict],
    formats: dict,
) -> None:
    """Write scenario/year/tariff rows starting at *col_base* (1-indexed Row Labels column)."""
    row_num = 6
    all_month_totals = [0.0] * 12
    has_data = [False] * 12

    for pt in pivot_tables:
        months_in_data: list[int] = pt["months"]
        pt_rows: list[dict] = pt["rows"]

        sc_agg = [sum(r["values"][i] for r in pt_rows) for i in range(len(months_in_data))]
        sc_vals = _month_values(months_in_data, sc_agg)
        sc_grand = sum(v for v in sc_vals if v is not None)

        _w(ws, row_num, col_base, str(pt["title"]), formats["bold_bottom"])
        for i, value in enumerate(sc_vals):
            _w(ws, row_num, col_base + i + 1, value, formats["bold_num_bottom"])
            if value is not None:
                all_month_totals[i] += value
                has_data[i] = True
        _w(ws, row_num, col_base + 13, sc_grand, formats["bold_num_bottom"])
        row_num += 1

        years: dict[int, list[dict]] = {}
        for row in pt_rows:
            years.setdefault(row["year"], []).append(row)

        for year in sorted(years):
            yr_rows = years[year]
            yr_agg = [sum(r["values"][i] for r in yr_rows) for i in range(len(months_in_data))]
            yr_vals = _month_values(months_in_data, yr_agg)
            yr_grand = sum(v for v in yr_vals if v is not None)

            _w(ws, row_num, col_base, str(year), formats["bold_indent1"])
            for i, value in enumerate(yr_vals):
                if value is not None:
                    _w(ws, row_num, col_base + i + 1, value, formats["bold_num"])
            _w(ws, row_num, col_base + 13, yr_grand, formats["bold_num"])
            row_num += 1

            for row in yr_rows:
                tariff_vals = _month_values(months_in_data, row["values"])
                tariff_grand = sum(v for v in tariff_vals if v is not None)
                _w(ws, row_num, col_base, row["tariff"], formats["indent2"])
                for i, value in enumerate(tariff_vals):
                    if value is not None:
                        _w(ws, row_num, col_base + i + 1, value, formats["num"])
                _w(ws, row_num, col_base + 13, tariff_grand, formats["num"])
                row_num += 1

    grand_total = sum(all_month_totals)
    _w(ws, row_num, col_base, "Grand Total", formats["bold_blue"])
    for i, value in enumerate(all_month_totals):
        if has_data[i]:
            _w(ws, row_num, col_base + i + 1, value, formats["bold_blue_num"])
        else:
            _w(ws, row_num, col_base + i + 1, None, formats["bold_blue"])
    _w(ws, row_num, col_base + 13, grand_total, formats["bold_blue_num"])


def _write_delta_sheet(
    wb: xlsxwriter.Workbook,
    sheet_name: str,
    delta_tables: list[dict],
    metric_col: str,
    output_type: str,
    formats: dict,
    filtered_delta_tables: list[dict] | None = None,
    filter_summary: dict[str, str] | None = None,
) -> None:
    # Filtered table starts 2 columns after the 4-column original (col 7).
    _FILT_BASE = 7

    ws = wb.add_worksheet(sheet_name)
    ws.hide_gridlines(2)
    ws.set_column(0, 0, 35)
    ws.set_column(1, 3, 25)

    _w(ws, 1, 1, "OUTPUT_TYPE", formats["blue"])
    _w(ws, 1, 2, output_type, formats["blue"])
    _w(ws, 2, 1, "MACHINE_NAME", formats["blue"])
    _w(ws, 2, 2, "(All)", formats["blue"])

    _write_delta_body(ws, 1, delta_tables, metric_col, formats)

    if filtered_delta_tables and filter_summary:
        ws.set_column(_FILT_BASE - 1, _FILT_BASE - 1, 35)
        ws.set_column(_FILT_BASE, _FILT_BASE + 3, 25)

        for row_i, (key, value) in enumerate(filter_summary.items(), start=1):
            _w(ws, row_i, _FILT_BASE, key, formats["blue"])
            _w(ws, row_i, _FILT_BASE + 1, value, formats["blue"])

        _write_delta_body(ws, _FILT_BASE, filtered_delta_tables, metric_col, formats)


def _write_delta_body(
    ws: xlsxwriter.worksheet.Worksheet,
    col_base: int,
    delta_tables: list[dict],
    metric_col: str,
    formats: dict,
) -> None:
    """Write delta-pair tables starting at *col_base* (1-indexed Row Labels column)."""
    row_num = 4

    for dt in delta_tables:
        right_name: str = dt["right_name"]
        left_name: str = dt["left_name"]
        right_total: float = dt["right_total"]
        left_total: float = dt["left_total"]
        delta_total: float = dt["delta_total"]
        dt_rows: list[dict] = dt["rows"]

        _w(ws, row_num, col_base,     "Row Labels",             formats["bold_blue_bottom"])
        _w(ws, row_num, col_base + 1, left_name,                formats["bold_blue_bottom"])
        _w(ws, row_num, col_base + 2, right_name,               formats["bold_blue_bottom"])
        _w(ws, row_num, col_base + 3, f"Dif of {metric_col}",   formats["bold_blue"])
        row_num += 1

        for row in dt_rows:
            _w(ws, row_num, col_base,     str(row["year"]),   formats["indent1"])
            _w(ws, row_num, col_base + 1, row["left_value"],  formats["num"])
            _w(ws, row_num, col_base + 2, row["right_value"], formats["num"])
            _w(ws, row_num, col_base + 3, row["delta"],       formats["num"])
            row_num += 1

        _w(ws, row_num, col_base,     "Grand Total",  formats["bold_blue_top"])
        _w(ws, row_num, col_base + 1, left_total,     formats["bold_blue_num_top"])
        _w(ws, row_num, col_base + 2, right_total,    formats["bold_blue_num_top"])
        _w(ws, row_num, col_base + 3, delta_total,    formats["bold_blue_num_top"])
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
