# Portfolio Layouts

This document specifies the **per-portfolio Excel layouts**, derived from the
analyst's screenshots. UK is unchanged; NL, DE, Hydro, and Nuclear use the new
**pivot layout** (scenarios as columns, metrics stacked as row groups). Each
non-UK portfolio needs both a **yearly** and a **monthly** view.

See [pivot-export-architecture.md](pivot-export-architecture.md) for how these
are produced and [portfolio-metrics-and-calculations.md](portfolio-metrics-and-calculations.md)
for the metrics referenced here.

## Common Pivot Anatomy (non-UK)

All non-UK pivots share this field layout:

| Pivot area | Field(s) |
|---|---|
| **Report filters** (page) | `COUNTRY`, `AS_OF_DATE` / `COD`, `MACHINE_NAME`, `OUTPUT_TYPE` |
| **Columns** | `SCENARIO_NAME` (2–4 scenarios) + labelled delta members |
| **Rows** | `METRIC` (outer, the `Sum of …` groups) → `YEAR` (yearly) or `MONTH` (monthly) (inner) |
| **Values** | `Sum of VALUE` |
| **Totals** | `Total Sum of <metric>` per metric group |

Formatting:

- **Currency** metrics (`IV`, `IV incl. Heat`, `EV`, `Heat Costs`, fuel/CO₂
  costs) use a `€ #,##0` style.
- **Numeric** metrics (`Power Position`, `Heat Production`, `Running Hours`,
  `Sum of Starts`, `Fuel Position GJ`) use `#,##0` (or `#,##0.000` where the
  screenshots show decimals).
- **Delta cells**: negative = red, positive = green (conditional formatting
  carried by the template).
- `FUEL_POS_TOT__UOM` is **not** a value field — shown as a label/annotation.

## Delta Columns

Delta columns appear to the **right of the scenario columns**. Each step delta
between consecutive scenarios uses a **user-supplied label**; the final
cumulative column is `Delta`. Examples from the screenshots:

| Portfolio | Scenario columns | Delta columns |
|---|---|---|
| NL | `NL_CSS_IV_M0_All_20260604_000600`, `…_UA` | `Delta (New-Old)`, `Delta %` |
| Hydro | `…_v1_HFC-new_…`, `…_v1`, `…_v2` | `Delta inflow`, `Delta grid`, `Delta` |
| Nuclear | `…_v1_20260608`, `…_v1`, `…_v2` | `Delta R4`, `Delta R3`, `Delta` |
| DE Hydro (EV) | `…_v1_…`, `…-ROR-2_EV`, `…-PU-int-2_EV`, `…-PU-ext-2_EV` | `Delta ROR`, `Delta PU-int`, `Delta PU-ext`, `Delta` |

Labels are entered by the user per step in the Configure UI (see
[frontend-portfolio-ux.md](frontend-portfolio-ux.md)) and carried into the
export as labelled delta members (see
[pivot-export-architecture.md](pivot-export-architecture.md)).

## NL

**Filters:** `COUNTRY=NL`, `AS_OF_DATE`, `MACHINE_NAME=(All)`, `OUTPUT_TYPE=IV`.

**Yearly view** — metric row-groups, years 2026–2029 as inner rows:

```
Sum of INTRINSIC_VALUE__CUR     | <scn1> | <scn2> | Delta (New-Old) | Delta %
  2026 / 2027 / 2028 / 2029
Sum of IV_INCL_HEAT_COSTS       | ...
Sum of POWER_POS__GWH           | ...
Sum of HEAT_PRODUCTION__GWH     | ...
Total Sum of INTRINSIC_VALUE__CUR ...
Total Sum of IV_INCL_HEAT_COSTS ...
Total Sum of POWER_POS__GWH ...
Total Sum of HEAT_PRODUCTION__GWH ...
```

**Monthly view** — same structure, months 1–12 (screenshot shows 6–12) as inner
rows. The monthly screenshot also includes `Sum of HEAT_COSTS` as a metric
group; this is one of the NL **optional** metrics and appears when selected.

**Optional NL metrics** (opt-in, off by default): `Adjusted Running Regime`
(`RUNNING_HOURS`), `SUM_STARTS`, `HEAT_COSTS`, `FUEL_POS_TOT__GJ`,
`FUEL_POS_TOT__UOM`, `FUEL_COST_ELEC__CUR`, `CO2_COST_ELEC__CUR`. Each selected
metric adds a `Sum of …` row group (UoM as label, not summed).

## DE

**Filters:** `AS_OF_DATE`, plus `COUNTRY`, `MACHINE_NAME`, `OUTPUT_TYPE`.
The DE Hydro screenshot is an **EV** view (`Sum of EXTRINSIC_VALUE`) with four
scenarios and three labelled step deltas + cumulative `Delta`.

**Default metrics:** `IV`, `Power Position`; **optional** `EV`.

**Yearly + monthly**: years/months as inner rows; `Grand Total` row at the
bottom for a single-metric view, or `Total Sum of <metric>` per group when
multiple metrics are selected.

## Hydro

**Filters:** `COD`/`AS_OF_DATE`, `MACHINE_NAME`, `OUTPUT_TYPE`.
Three scenarios; deltas `Delta inflow`, `Delta grid`, `Delta`. Plain numeric
formatting (no currency symbol on the IV figures in the screenshot — confirm
desired currency formatting with the analyst).

**Metrics:** `POWER_POS__GWH`, `INTRINSIC_VALUE__CUR`.

```
Sum of POWER_POS__GWH      | scn1 | scn2 | scn3 | Delta inflow | Delta grid | Delta
  2026 / 2027 / 2028 / 2029
Sum of INTRINSIC_VALUE__CUR | ...
Total Sum of POWER_POS__GWH ...
Total Sum of INTRINSIC_VALUE__CUR ...
```

## Nuclear

**Filters:** `AS_OF_DATE`, `MACHINE_NAME`, `OUTPUT_TYPE`.
Three scenarios; deltas `Delta R4`, `Delta R3`, `Delta`.

**Metrics:** `POWER_POS__GWH`, `INTRINSIC_VALUE__CUR`. Same yearly/monthly
structure as Hydro.

## UK (Unchanged)

UK keeps the current layout: one sheet per metric with **months as columns**,
years/tariffs as rows, plus the existing delta and machine-delta sheets, and
peak/offpeak retained as a row dimension. No changes.

## Template Authoring Checklist

For each non-UK portfolio + view, author a template pivot with:

- [ ] Page filters: `COUNTRY`, `AS_OF_DATE`, `MACHINE_NAME`, `OUTPUT_TYPE`.
- [ ] Column field: `SCENARIO_NAME` (+ delta members).
- [ ] Row fields: `METRIC` then `YEAR` (yearly) or `MONTH` (monthly).
- [ ] Value field: `Sum of VALUE` with the correct number format per metric.
- [ ] Subtotals enabled to render `Total Sum of <metric>`.
- [ ] Conditional formatting for delta red/green.
- [ ] `Refresh data when opening the file` enabled on the pivot cache.

## Open Items to Confirm

1. Currency vs. plain formatting for **Hydro** IV figures (screenshot shows no
   `€`).
2. Whether `Delta %` is needed beyond NL.
3. Exact month range for monthly views (full 1–12 vs. from current month).
