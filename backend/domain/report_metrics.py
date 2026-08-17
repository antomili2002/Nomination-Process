from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import pandas as pd
from pandas.api.types import is_numeric_dtype

from backend.core.constants import (
    DIMENSION_COLS,
    EV_COL,
    HEAT_PRODUCTION_COL,
    IV_COL,
    IV_INCL_HEAT_COSTS_COL,
    POWER_POS_COL,
)

ChainKind = Literal["iv", "ev"]

# Excel sheet names are capped at 31 chars; leave room for "_month"/"_sheet".
_EXCEL_PREFIX_MAX_LEN = 20


@dataclass(frozen=True)
class ReportMetric:
    key: str
    column: str
    label: str
    output_type: str
    chain_kind: ChainKind
    excel_prefix: str
    category: str
    default_selected: bool


_CORE_CATEGORY = "Core Value Metrics"

# Curated metrics with hand-picked labels/prefixes. Any other numeric column
# found in an uploaded file is turned into a ReportMetric dynamically by
# ``available_metrics`` below.
REPORT_METRICS: tuple[ReportMetric, ...] = (
    ReportMetric(
        key="ev",
        column=EV_COL,
        label="Extrinsic Value",
        output_type="EV",
        chain_kind="ev",
        excel_prefix="EV",
        category=_CORE_CATEGORY,
        default_selected=True,
    ),
    ReportMetric(
        key="iv",
        column=IV_COL,
        label="Intrinsic Value",
        output_type="IV",
        chain_kind="iv",
        excel_prefix="IV",
        category=_CORE_CATEGORY,
        default_selected=True,
    ),
    ReportMetric(
        key="pp",
        column=POWER_POS_COL,
        label="Power Position",
        output_type="IV",
        chain_kind="iv",
        excel_prefix="PP",
        category=_CORE_CATEGORY,
        default_selected=True,
    ),
    ReportMetric(
        key="iv_heat",
        column=IV_INCL_HEAT_COSTS_COL,
        label="IV incl. heat costs",
        output_type="IV",
        chain_kind="iv",
        excel_prefix="IV_Heat",
        category=_CORE_CATEGORY,
        default_selected=False,
    ),
    ReportMetric(
        key="heat_prod",
        column=HEAT_PRODUCTION_COL,
        label="Heat Production",
        output_type="IV",
        chain_kind="iv",
        excel_prefix="Heat_Prod",
        category=_CORE_CATEGORY,
        default_selected=False,
    ),
)


REPORT_METRIC_BY_KEY = {metric.key: metric for metric in REPORT_METRICS}


def available_metrics(data_df: pd.DataFrame) -> tuple[ReportMetric, ...]:
    """Return every metric selectable for this upload.

    Starts with the curated ``REPORT_METRICS`` that have a matching numeric
    column in the file, then appends a dynamically built ``ReportMetric`` for
    every other numeric column in the Data sheet. Dimension/identifier
    columns (scenario, year, month, tariff, machine, ...) are never metrics.
    Newly discovered metrics always aggregate via the IV chain, since only
    EXTRINSIC_VALUE is inherently tied to the EV chain.
    """
    metrics: list[ReportMetric] = []
    seen_columns: set[str] = set()

    for metric in REPORT_METRICS:
        if metric.column in data_df.columns and is_numeric_dtype(data_df[metric.column]):
            metrics.append(metric)
            seen_columns.add(metric.column)

    dimension_cols = set(DIMENSION_COLS)
    for column in data_df.columns:
        if column in dimension_cols or column in seen_columns:
            continue
        if is_numeric_dtype(data_df[column]):
            metrics.append(_build_dynamic_metric(column))
            seen_columns.add(column)

    return tuple(metrics)


def _build_dynamic_metric(column: str) -> ReportMetric:
    return ReportMetric(
        key=column,
        column=column,
        label=_humanize_column(column),
        output_type="IV",
        chain_kind="iv",
        excel_prefix=_sanitize_excel_prefix(column),
        category=_categorize_column(column),
        default_selected=False,
    )


def _humanize_column(column: str) -> str:
    if "__" in column:
        base, unit = column.split("__", 1)
        return f"{base.replace('_', ' ').title()} ({unit})"
    return column.replace("_", " ").title()


def _sanitize_excel_prefix(column: str) -> str:
    prefix = re.sub(r"[^A-Za-z0-9_]", "_", column)
    return prefix[:_EXCEL_PREFIX_MAX_LEN]


# Ordered keyword rules used to group dynamically discovered metrics into
# readable categories in the metric-selection UI. First match wins.
_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Running Regime", ("HOURS", "STARTS", "AVAILABILITY", "CAPACITY")),
    ("Fuel", ("FUEL",)),
    ("Emissions (CO2 / SO2 / NOx)", ("CO2", "SO2", "NOX", "DUST")),
    ("Water", ("WATER",)),
    ("Ancillary Services (FCR)", ("FCR",)),
    ("Pricing", ("PRICE", "_EUR_", "GC_VOLUME", "GC_COST")),
    ("Costs", ("COST",)),
)


def _categorize_column(column: str) -> str:
    upper = column.upper()
    for category, keywords in _CATEGORY_RULES:
        if any(keyword in upper for keyword in keywords):
            return category
    return "Other Metrics"

