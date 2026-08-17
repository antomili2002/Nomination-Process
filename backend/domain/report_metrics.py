from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.core.constants import (
    EV_COL,
    HEAT_PRODUCTION_COL,
    IV_COL,
    IV_INCL_HEAT_COSTS_COL,
    POWER_POS_COL,
)

ChainKind = Literal["iv", "ev"]


@dataclass(frozen=True)
class ReportMetric:
    key: str
    column: str
    label: str
    output_type: str
    chain_kind: ChainKind
    monthly_field: str
    deltas_field: str
    excel_prefix: str


REPORT_METRICS: tuple[ReportMetric, ...] = (
    ReportMetric(
        key="ev",
        column=EV_COL,
        label="Extrinsic Value",
        output_type="EV",
        chain_kind="ev",
        monthly_field="ev_monthly",
        deltas_field="ev_deltas",
        excel_prefix="EV",
    ),
    ReportMetric(
        key="iv",
        column=IV_COL,
        label="Intrinsic Value",
        output_type="IV",
        chain_kind="iv",
        monthly_field="iv_monthly",
        deltas_field="iv_deltas",
        excel_prefix="IV",
    ),
    ReportMetric(
        key="pp",
        column=POWER_POS_COL,
        label="Power Position",
        output_type="IV",
        chain_kind="iv",
        monthly_field="pp_monthly",
        deltas_field="pp_deltas",
        excel_prefix="PP",
    ),
    ReportMetric(
        key="iv_heat",
        column=IV_INCL_HEAT_COSTS_COL,
        label="IV incl. heat costs",
        output_type="IV",
        chain_kind="iv",
        monthly_field="iv_heat_monthly",
        deltas_field="iv_heat_deltas",
        excel_prefix="IV_Heat",
    ),
    ReportMetric(
        key="heat_prod",
        column=HEAT_PRODUCTION_COL,
        label="Heat Production",
        output_type="IV",
        chain_kind="iv",
        monthly_field="heat_prod_monthly",
        deltas_field="heat_prod_deltas",
        excel_prefix="Heat_Prod",
    ),
)


REPORT_METRIC_BY_KEY = {metric.key: metric for metric in REPORT_METRICS}
