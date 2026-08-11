# Pivot Export Architecture

This document describes the redesign of the Excel export so that **all delta
tables ship as native, interactive Excel PivotTables**, alongside the **raw
`Data` sheet** and the **`Info` sheet**. The goal is full flexibility for the
portfolio analyst: drag-and-drop fields, filters, slicers, and drill-down — the
behaviour visible in the target screenshots.

This supersedes the static, row-by-row export in
`backend/excel/report_writer.py` for the new pivot-layout portfolios. UK keeps
its current export (see "UK Compatibility" below).

## Why the Export Engine Must Change

The current writer uses **XlsxWriter**, which **cannot create native Excel
PivotTable objects** (it can only write static cells). `df.pivot_table().to_excel()`
also produces a *static* flattened table, not an interactive pivot. To deliver
genuine PivotTables we change the assembly engine.

### Options considered

| Approach | Native pivots | Effort | Risk | Decision |
|---|---|---|---|---|
| A. XlsxWriter static tables | No | — | — | Rejected (not pivots) |
| B. Programmatic OOXML pivot generation (hand-build `pivotCacheDefinition`, `pivotCacheRecords`, `pivotTable` parts) | Yes | High | High (Excel "repair" prompts) | Fallback |
| **C. Template workbooks + openpyxl fill** | **Yes** | **Medium** | **Low** | **Chosen** |

### Chosen approach: template workbooks

Maintain a small set of **template `.xlsx` files** (one per portfolio + view, or
one parameterised template) under `backend/excel/templates/`. Each template is
authored **once in Excel** and contains:

1. A **`Data`** sheet whose used range is an **Excel Table** (or dynamic named
   range) — this is the pivot **source**.
2. An **`Info`** sheet placeholder.
3. One **PivotTable sheet per metric/view**, pre-configured to match the
   screenshots (filters, row/column/value fields, number formats, styling).
4. Each pivot's cache set to **`refreshOnLoad = true`** so Excel rebuilds the
   pivots from the freshly written data the moment the file is opened.

At export time the pipeline:

1. Loads the template with **openpyxl** (`keep_vba=False`), which **preserves**
   the existing pivot definitions on round-trip.
2. Clears and writes the cleaned **long-format** data into the `Data` table,
   resizing the table/named range to the new row count.
3. Writes the **`Info`** sheet (raw copy of the upload's Info sheet).
4. Writes report metadata (`COUNTRY`, `AS_OF_DATE`) into the pivot **page/filter**
   defaults or a metadata cell.
5. Ensures `pivotCache.refreshOnLoad = True` on every pivot.
6. Saves to bytes and returns them.

> **openpyxl caveat:** openpyxl preserves existing PivotTables but does **not**
> let you author new ones from scratch reliably. That is exactly why the pivots
> are pre-built in the template and only their **source data** is replaced.
> Validate round-trips (see "Verification") because some openpyxl versions drop
> caches on save; pin a known-good version and add a regression test that opens
> the output and asserts the pivot parts still exist.

## The `Data` Sheet (Pivot Source)

A single **tidy, long-format** sheet feeds every pivot. One row per observation:

| Column | Example | Notes |
|---|---|---|
| `COUNTRY` | `NL` | pivot filter |
| `AS_OF_DATE` | `2026-06-04` | pivot filter (user-entered) |
| `OUTPUT_TYPE` | `IV` | pivot filter (`IV` / `EV`) |
| `SCENARIO_NAME` | `NL_CSS_IV_M0_All_20260604_000600` | pivot **column** field |
| `MACHINE_NAME` | `(All)` rows expanded per machine | pivot filter |
| `YEAR` | `2026` | pivot **row** field (yearly view) |
| `MONTH` | `6` | pivot **row** field (monthly view) |
| `TARIFF` | `peak` / `offpeak` | **UK only**; omitted/blank for non-UK |
| `METRIC` | `INTRINSIC_VALUE__CUR` | pivot **row** field (the `Sum of …` groups) |
| `VALUE` | `28690.0` | pivot **value** field (`Sum`) |
| `UOM` | `GJ` | only populated for `FUEL_POS_TOT__GJ`; non-aggregated |

Because the source is long format with a `METRIC` dimension, the pivots can
stack multiple metrics as row groups (`Sum of INTRINSIC_VALUE__CUR`,
`Sum of POWER_POS__GWH`, …) exactly like the screenshots, and the analyst can
freely re-pivot.

## How Delta Columns Live in the Pivots

Native pivots cannot, by themselves, produce **multiple custom-labelled step
deltas** (`Delta inflow`, `Delta grid`, `Delta R4`, `Delta ROR`, …) as
drag-drop fields. The chosen model is **hybrid (option C from the plan)**:

1. **Raw scenario values** are pivot fields (full flexibility: the analyst can
   pivot any scenario × metric × year/month).
2. **Pre-computed labelled deltas** are added to the source as additional
   `SCENARIO_NAME` members. For each step pair and the cumulative pair, the
   backend emits synthetic "scenario" columns whose `VALUE` is the delta and
   whose name is the user label, e.g. `Δ inflow`, `Δ grid`, `Δ` (cumulative).
   These appear as their own columns in the pivot, reproducing the screenshots,
   while remaining part of the same flexible pivot.
3. **`Delta %`** (NL) is realised either as a pre-computed `Δ% …` member or via
   the pivot's *Show Values As → % Difference From*. The template encodes the
   chosen method.

This keeps one source table, one set of pivots, full flexibility, **and** the
exact labelled delta columns the analyst expects.

> Alternative (option B, documented for completeness): expose only raw scenarios
> and let the analyst use *Show Values As → Difference From* for deltas. This is
> fully dynamic but loses the custom step labels, so it is not the default.

## Sheets in the Exported Workbook

For pivot-layout portfolios (NL/DE/Hydro/Nuclear):

| Sheet | Content |
|---|---|
| `Data` | Tidy long-format source (table) — always exported |
| `Info` | Raw copy of the upload's Info sheet — always exported |
| `<Metric/View> Pivot` sheets | One native PivotTable per metric/view, per the layout spec |

For UK: unchanged (`<prefix>_month`, `<prefix>_sheet`, `<prefix>_machine_sheet`,
`Info`, `Data`).

## Pipeline and Touch Points

```text
download_service.create_excel_report()
  -> report_service.generate_report_from_workbook()   # aggregated long frame
  -> pivot_export.write_pivot_report(report, info_df, portfolio, as_of_date)
       - load template for portfolio
       - write Data table (long format, incl. labelled delta members)
       - write Info sheet
       - set filters + refreshOnLoad
       - return bytes
```

| Concern | File |
|---|---|
| New template-based writer | `backend/excel/pivot_export.py` (new) |
| Template workbooks | `backend/excel/templates/*.xlsx` (new) |
| Long-format source builder | `backend/processing/report_builder.py` (add `build_pivot_source()`) |
| Export routing by layout | `backend/services/download_service.py` |
| UK writer (unchanged) | `backend/excel/report_writer.py` |
| openpyxl dependency | `requirements.txt` (add `openpyxl`) |

## UK Compatibility

UK uploads continue through `report_writer.py` (XlsxWriter) with byte-compatible
output. `download_service` branches on
`PortfolioConfig.layout`: `UK_CLASSIC → report_writer`, `PIVOT → pivot_export`.

## Verification

- **Round-trip integrity**: generate a pivot workbook, reopen with openpyxl,
  assert each expected `PivotTable` and `pivotCache` part is present and
  `refreshOnLoad` is set.
- **No-repair open**: manual check that Excel opens the file without a "repair"
  prompt and pivots show data after the on-open refresh.
- **Source correctness**: assert the `Data` table row count and schema, and that
  labelled delta members are present with correct values.
- **UK regression**: existing UK export tests stay green.
