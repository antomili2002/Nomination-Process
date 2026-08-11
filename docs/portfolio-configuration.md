# Portfolio Configuration

This document describes the **portfolio registry** — a single source of truth
that turns the current single-layout (UK-only) report engine into a
portfolio-driven system. The portfolio of an upload determines:

- which **value columns (metrics)** are available and selected by default,
- which **Excel layout** the export uses (UK-classic vs. the new
  scenarios-as-columns pivot layout),
- whether **peak/offpeak** tariff splitting applies,
- the **delta model** (single delta vs. multiple labelled step deltas),
- the **number/currency formatting** of each metric.

It is the foundation for the changes documented in
[portfolio-metrics-and-calculations.md](portfolio-metrics-and-calculations.md),
[portfolio-layouts.md](portfolio-layouts.md),
[pivot-export-architecture.md](pivot-export-architecture.md),
[value-column-selection.md](value-column-selection.md), and
[frontend-portfolio-ux.md](frontend-portfolio-ux.md).

## Supported Portfolios

| Portfolio | Peak/Offpeak | Layout | Default metrics |
|---|---|---|---|
| `UK`      | Yes | UK-classic (months as columns, one metric per sheet) | EV, IV, Power Position |
| `NL`      | No  | Pivot (scenarios as columns) | IV, IV incl. Heat, Power Position, Heat Production |
| `DE`      | No  | Pivot (scenarios as columns) | IV, Power Position (EV when present) |
| `Hydro`   | No  | Pivot (scenarios as columns) | IV, Power Position |
| `Nuclear` | No  | Pivot (scenarios as columns) | IV, Power Position |

> UK keeps its **current** layout and output unchanged. Only `NL`, `DE`,
> `Hydro`, and `Nuclear` use the new pivot layout.

## Detection

The portfolio is **auto-detected** from the workbook, with a deterministic
fallback chain so that asset types (`Hydro`, `Nuclear`) that are not literal
market areas are still classified correctly.

Resolution order (first match wins):

1. **`MARKET_AREA` value** on the Info sheet
   (`ScenarioInfo.market_area`): `UK`, `NL`, `DE` map directly.
2. **Scenario name pattern** (case-insensitive) for asset types that share a
   market area: tokens `_Hydro_` / `_Nuclear_` in `SCENARIO_NAME`
   (e.g. `20260413_NO_Hydro_GIF_v1`, `20260608_NO_Nuclear_GIF_v1`) classify the
   upload as `Hydro` / `Nuclear` respectively.
3. **Fallback**: `UK` (preserves today's behaviour for legacy uploads).

Detection happens once, during upload processing, and is stored on the
processed-upload artifact so every later request (preview, generate, export)
reuses it. The detected portfolio is also returned to the frontend so the UI
can adapt (see [frontend-portfolio-ux.md](frontend-portfolio-ux.md)).

> **Open item to confirm with the analyst:** whether a single upload can ever
> mix portfolios. The current design assumes **one portfolio per upload**. If
> mixed uploads are possible, detection must move from the workbook level to the
> scenario level.

## The Registry

A new module `backend/domain/portfolios.py` holds a frozen registry. It does
**not** replace `backend/domain/report_metrics.py`; it composes it. Each
portfolio references metric keys defined in the metric registry (see
[portfolio-metrics-and-calculations.md](portfolio-metrics-and-calculations.md)).

```python
# backend/domain/portfolios.py  (illustrative)
from dataclasses import dataclass
from enum import Enum


class LayoutKind(str, Enum):
    UK_CLASSIC = "uk_classic"   # months as columns, one metric per sheet
    PIVOT = "pivot"             # scenarios as columns, metrics stacked as rows


@dataclass(frozen=True)
class PortfolioConfig:
    key: str                       # "UK", "NL", "DE", "Hydro", "Nuclear"
    label: str                     # human label shown in the UI / header
    layout: LayoutKind
    peak_offpeak: bool             # True only for UK
    default_metric_keys: tuple[str, ...]   # pre-selected value columns
    optional_metric_keys: tuple[str, ...]  # opt-in (NL extras, etc.)
    show_delta_pct: bool           # NL shows a "Delta %" column
    name_patterns: tuple[str, ...] # regex tokens for detection fallback


PORTFOLIOS: dict[str, PortfolioConfig] = {
    "UK": PortfolioConfig(
        key="UK", label="UK", layout=LayoutKind.UK_CLASSIC,
        peak_offpeak=True,
        default_metric_keys=("ev", "iv", "pp"),
        optional_metric_keys=(),
        show_delta_pct=False,
        name_patterns=(),
    ),
    "NL": PortfolioConfig(
        key="NL", label="NL", layout=LayoutKind.PIVOT,
        peak_offpeak=False,
        default_metric_keys=("iv", "iv_heat", "pp", "heat_prod"),
        optional_metric_keys=(
            "running_hours", "sum_starts", "heat_costs",
            "fuel_pos_gj", "fuel_pos_uom",
            "fuel_cost_elec", "co2_cost_elec",
        ),
        show_delta_pct=True,
        name_patterns=(),
    ),
    "DE": PortfolioConfig(
        key="DE", label="DE", layout=LayoutKind.PIVOT,
        peak_offpeak=False,
        default_metric_keys=("iv", "pp"),
        optional_metric_keys=("ev",),
        show_delta_pct=False,
        name_patterns=(r"_DE_",),
    ),
    "Hydro": PortfolioConfig(
        key="Hydro", label="Hydro", layout=LayoutKind.PIVOT,
        peak_offpeak=False,
        default_metric_keys=("iv", "pp"),
        optional_metric_keys=(),
        show_delta_pct=False,
        name_patterns=(r"_Hydro_",),
    ),
    "Nuclear": PortfolioConfig(
        key="Nuclear", label="Nuclear", layout=LayoutKind.PIVOT,
        peak_offpeak=False,
        default_metric_keys=("iv", "pp"),
        optional_metric_keys=(),
        show_delta_pct=False,
        name_patterns=(r"_Nuclear_",),
    ),
}


def detect_portfolio(scenarios_df, default: str = "UK") -> str:
    """Resolve the portfolio from MARKET_AREA, then scenario-name patterns."""
    ...
```

## As-of Date

The pivot filters in the target layouts include an `AS_OF_DATE` / `COD`
selector. This value is **entered by the user** at upload/configure time (it is
not read from the Data sheet). It flows through the API to the export and is
written to the pivot filter / a report-metadata cell. See
[frontend-portfolio-ux.md](frontend-portfolio-ux.md) for the input control and
[pivot-export-architecture.md](pivot-export-architecture.md) for where it lands
in the workbook.

## Touch Points

| Concern | File |
|---|---|
| Registry + detection | `backend/domain/portfolios.py` (new) |
| Metric definitions | `backend/domain/report_metrics.py` |
| Column constants | `backend/core/constants.py` |
| Detection wired into upload | `backend/services/upload_service.py` |
| Persisted on artifact | `backend/storage/processed_uploads.py`, `backend/domain/workbook.py` |
| Surfaced to API | `backend/api/schemas.py`, `backend/api/routes_upload.py` |

## Verification

- Unit test `detect_portfolio` for each market area and for the
  `Hydro`/`Nuclear` name-pattern fallback, plus the legacy `UK` default.
- Assert UK uploads still resolve to `LayoutKind.UK_CLASSIC` with
  `peak_offpeak=True` so existing output is unaffected.
