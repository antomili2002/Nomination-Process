# Frontend Portfolio UX

This document describes the frontend changes that make the app
**portfolio-aware**: dynamic sections, per-step delta labels, an as-of-date
input, value-column selection, and removal of the hard-coded header. The
existing three-step flow (Upload → Configure → Result) is preserved.

Related: [portfolio-configuration.md](portfolio-configuration.md),
[value-column-selection.md](value-column-selection.md),
[portfolio-layouts.md](portfolio-layouts.md).

## Upload Page

- After upload, the response now includes `portfolio`, `available_metrics`, and
  `default_metrics` (see [value-column-selection.md](value-column-selection.md)).
- Display the **detected portfolio** (e.g. a badge "Portfolio: NL") with a
  manual override dropdown as a safety net (in case detection is wrong).
- Store `portfolio` and metric metadata in `uploadCtx` for later steps.

Touch: `frontend/src/pages/UploadPage.tsx`, `frontend/src/App.tsx`,
`frontend/src/types/*`.

## Configure Page

Three additions:

1. **Value-column selection** — a checkbox group titled "Value columns",
   pre-filled with `default_metrics`; optional metrics shown unchecked. Enforce
   at least one selected. Send as `selected_metrics`.
2. **Per-step delta labels** — in the chain builder, render a small text input
   next to each consecutive scenario pair so the user names that step delta
   (e.g. `inflow`, `grid`, `R4`, `ROR`). The cumulative delta is fixed as
   `Delta`. Collected as `delta_labels: { stepIndex: string }` and sent with
   generate/export.
3. **As-of date** — a date input (`AS_OF_DATE` / `COD`), defaulting to today,
   sent as `as_of_date`. This populates the pivot filter in the export.

For **UK**, the delta-label inputs and as-of-date can be hidden (UK keeps its
current layout); show them only when `portfolio !== "UK"`.

Touch: `frontend/src/pages/ConfigurePage.tsx`,
`frontend/src/pages/scenarioChains.ts`.

## Result Page

- The section sidebar is built from the **selected metrics** and the portfolio's
  layout, not the fixed 15-section list. Non-UK portfolios show the
  yearly/monthly pivot sections; UK shows its existing sections.
- Hide peak/offpeak (tariff) columns when `portfolio.peak_offpeak === false`.
- Keep the machine filter and caching behaviour.
- The **Download** button sends `portfolio`, `selected_metrics`, `delta_labels`,
  and `as_of_date` alongside the existing `upload_id`, `iv_chain`, `ev_chain`,
  and `selected_machines`.

Touch: `frontend/src/pages/ResultPage.tsx`,
`frontend/src/components/report/ReportSections.tsx`.

## Report Metrics Config

`frontend/src/reportMetrics.ts` currently hard-codes 5 groups × 3 table types.
Refactor so the section list is **derived** from:

- the detected `portfolio` (layout variant),
- the `selected_metrics`,
- the available views (yearly/monthly for pivot portfolios).

Add the new NL metric definitions (Adjusted Running Regime, Sum of Starts, Heat
Costs, Fuel Position GJ/UoM, Fuel Cost Elec, CO₂ Cost Elec) with their display
labels and formats, mirroring the backend registry.

## Header

`frontend/src/components/Header.tsx` hard-codes `"UK · EG"`. Replace with the
**detected portfolio label** from `uploadCtx` (fallback to a neutral default
before upload).

## Types

Extend `frontend/src/types/report.ts`:

- `ReportData` gains `portfolio` and the new metric arrays as needed.
- New `MetricOption` type (`{ key, label, format, optional }`).
- Delta tables carry an optional `label` for the custom step name.

## Display Formatting

- Currency metrics → `€` thousands formatting; numeric metrics → plain
  thousands; match [portfolio-layouts.md](portfolio-layouts.md).
- Delta cells: red negative, green/blue positive (existing `fmtDelta` extended).
- `Fuel Position UoM` rendered as a label, never summed.

## Verification

- Uploading an NL fixture shows "Portfolio: NL", NL default metrics checked, NL
  extras available but unchecked, and no peak/offpeak columns.
- Entering step labels produces matching delta-column headers in the Result
  tables and the exported pivots.
- UK upload is visually unchanged.
