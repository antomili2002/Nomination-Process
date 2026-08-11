# Portfolio Metrics and Calculations

This document extends the metric registry
(`backend/domain/report_metrics.py`) and the column constants
(`backend/core/constants.py`) to cover the additional NL value columns, and
specifies the per-portfolio calculation rules. It builds on
[report-metrics-v2.md](report-metrics-v2.md) and
[portfolio-configuration.md](portfolio-configuration.md).

## New Source Columns

These columns already exist in the uploaded `Data` sheet and only need to be
registered (added to `METRIC_COLS` for numeric coercion and exposed as
`ReportMetric`s):

| Constant | Column | Meaning | Type |
|---|---|---|---|
| `RUNNING_HOURS_COL` | `RUNNING_HOURS` | "Adjusted Running Regime" | numeric (hours) |
| `SUM_STARTS_COL` | `SUM_STARTS` | number of starts | numeric (count) |
| `HEAT_COSTS_COL` | `HEAT_COSTS` | heat costs | currency |
| `FUEL_POS_GJ_COL` | `FUEL_POS_TOT__GJ` | total fuel position | numeric (GJ) |
| `FUEL_POS_UOM_COL` | `FUEL_POS_TOT__UOM` | fuel position unit of measure | **text / label** |
| `FUEL_COST_ELEC_COL` | `FUEL_COST_ELEC__CUR` | electricity fuel cost | currency |
| `CO2_COST_ELEC_COL` | `CO2_COST_ELEC__CUR` | electricity CO₂ cost | currency |

> **`FUEL_POS_TOT__UOM` is not a summable value** — it is a unit-of-measure
> label. It must not be aggregated with `Sum`. Treat it as metadata: display it
> as a label/annotation next to `FUEL_POS_TOT__GJ`, or expose it as a pivot
> **filter/row label** rather than a value field. See
> [portfolio-layouts.md](portfolio-layouts.md).

## Updated Metric Registry

Existing metrics are unchanged; new metrics are appended. `Display name`
matches the `Sum of …` label seen in the target pivots.

| Key | Column | Output type | Chain | Display name | Format |
|---|---|---|---|---|---|
| `ev` | `EXTRINSIC_VALUE` | EV | EV | Extrinsic Value | currency |
| `iv` | `INTRINSIC_VALUE__CUR` | IV | IV | Intrinsic Value | currency |
| `pp` | `POWER_POS__GWH` | IV | IV | Power Position | number (GWh) |
| `iv_heat` | `IV_INCL_HEAT_COSTS` | IV | IV | IV incl. Heat Costs | currency |
| `heat_prod` | `HEAT_PRODUCTION__GWH` | IV | IV | Heat Production | number (GWh) |
| `running_hours` | `RUNNING_HOURS` | IV | IV | Adjusted Running Regime | number (h) |
| `sum_starts` | `SUM_STARTS` | IV | IV | Sum of Starts | number |
| `heat_costs` | `HEAT_COSTS` | IV | IV | Heat Costs | currency |
| `fuel_pos_gj` | `FUEL_POS_TOT__GJ` | IV | IV | Fuel Position (GJ) | number (GJ) |
| `fuel_pos_uom` | `FUEL_POS_TOT__UOM` | IV | IV | Fuel Position UoM | text (no aggregation) |
| `fuel_cost_elec` | `FUEL_COST_ELEC__CUR` | IV | IV | Fuel Cost Elec | currency |
| `co2_cost_elec` | `CO2_COST_ELEC__CUR` | IV | IV | CO₂ Cost Elec | currency |

### `ReportMetric` additions

Add two fields to the `ReportMetric` dataclass to support the new behaviour:

- `aggregation: str = "sum"` — `"sum"` for numeric metrics, `"none"` for
  `fuel_pos_uom` (carried through as a label, never summed).
- `value_format: str` — `"currency"` or `"number"` or `"text"`, used by the
  export to pick the cell number format and by the frontend for display.

These are additive and backward compatible; existing rows default
`aggregation="sum"` and keep their current formatting.

## Per-Portfolio Default and Optional Metrics

Driven by `PortfolioConfig.default_metric_keys` / `optional_metric_keys`
(see [portfolio-configuration.md](portfolio-configuration.md)):

- **UK** — `ev`, `iv`, `pp`. (No change.)
- **NL** — defaults `iv`, `iv_heat`, `pp`, `heat_prod`; **optional (opt-in,
  off by default)** `running_hours`, `sum_starts`, `heat_costs`,
  `fuel_pos_gj`, `fuel_pos_uom`, `fuel_cost_elec`, `co2_cost_elec`.
- **DE** — defaults `iv`, `pp`; optional `ev` (the DE Hydro EV view shows
  `Sum of EXTRINSIC_VALUE`).
- **Hydro** — `iv`, `pp`.
- **Nuclear** — `iv`, `pp`.

The user can refine the selection per report (see
[value-column-selection.md](value-column-selection.md)); the portfolio only
provides the starting set.

## Aggregation Rules

All numeric metrics aggregate by **sum**, consistent with the current pipeline
(`backend/processing/monthly_output.py`).

- **Yearly view**: group by the configured keys and sum to one value per year.
- **Monthly view**: group to one value per month.
- **Grouping keys**:
  - UK: `[SCENARIO_NAME, TARIFF, YEAR, MONTH]` (tariff retained for peak/offpeak).
  - Non-UK: `[SCENARIO_NAME, YEAR, MONTH]` — **`TARIFF` is dropped** because
    peak/offpeak does not apply. `MACHINE_NAME` continues to be summed across
    (matching the pivot `MACHINE_NAME = (All)` filter), unless a machine filter
    is applied.
- **`fuel_pos_uom`**: not summed. Within a (scenario, year[/month]) group the
  unit is expected to be constant; carry the distinct value through. If multiple
  units appear in a group, surface a validation warning rather than silently
  picking one.

See [pivot-export-architecture.md](pivot-export-architecture.md) for how the
aggregated long-format frame becomes the pivot data source.

## Delta Calculations

Deltas reuse the existing step/cumulative model
(`backend/processing/chain_builder.py`,
`backend/processing/delta_output.py`,
`backend/processing/yearly_delta_output.py`):

- One **step delta** per consecutive scenario pair in the chain, plus a
  **cumulative** delta (base → final) when the chain has 3+ scenarios.
- Each step delta gets a **user-supplied label** (e.g. `inflow`, `grid`,
  `R4`, `R3`, `ROR`, `PU-int`, `PU-ext`). The cumulative column is labelled
  `Delta`. See [portfolio-layouts.md](portfolio-layouts.md).
- **NL** additionally shows **`Delta %`** computed as
  `(right - left) / left`, rendered blank/`0%` when `left == 0`
  (matches the NL screenshots).

## Touch Points

| Concern | File |
|---|---|
| Column constants + `METRIC_COLS` | `backend/core/constants.py` |
| Metric registry + new fields | `backend/domain/report_metrics.py` |
| Numeric coercion of new columns | `backend/processing/cleaning.py` |
| Required-column validation | `backend/core/constants.py` (`REQUIRED_DATA_COLS`) — keep new cols **optional** |
| Aggregation key selection | `backend/processing/monthly_output.py` |

## Verification

- Coercion tests for the new columns (including European decimal commas).
- A metric registered with `aggregation="none"` (`fuel_pos_uom`) is never
  passed to a sum and is carried as text.
- `REQUIRED_DATA_COLS` unchanged for UK; new columns are optional so existing
  UK uploads without them still validate.
- `Delta %` returns `None`/blank when the base value is zero.
