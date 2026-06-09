# Report Metrics V2

This document describes the metric-driven report structure introduced for
`IV_INCL_HEAT_COSTS` and `HEAT_PRODUCTION__GWH`.

## What Changed

Reports are no longer built by hard-coding each metric in
`backend/services/report_service.py`. Metric metadata now lives in
`backend/domain/report_metrics.py`, and reusable construction logic lives in
`backend/processing/report_builder.py`.

Each `ReportMetric` defines:

- `key`: internal stable identifier, for example `iv_heat`.
- `column`: source column in the Excel `Data` sheet.
- `label`: display label for humans.
- `output_type`: Excel filter display value, usually `IV` or `EV`.
- `chain_kind`: which scenario chain to use, `iv` or `ev`.
- `monthly_field`, `deltas_field`, `machine_deltas_field`: backend JSON keys.
- `excel_prefix`: sheet-name prefix used by Excel export.

The current report metrics are:

| Key | Column | Chain | Excel prefix |
|---|---|---|---|
| `ev` | `EXTRINSIC_VALUE` | EV | `EV` |
| `iv` | `INTRINSIC_VALUE__CUR` | IV | `IV` |
| `pp` | `POWER_POS__GWH` | IV | `PP` |
| `iv_heat` | `IV_INCL_HEAT_COSTS` | IV | `IV_Heat` |
| `heat_prod` | `HEAT_PRODUCTION__GWH` | IV | `Heat_Prod` |

## Backend Flow

`POST /reports/generate` now follows this shape:

1. `routes_reports.py` receives the request and maps domain errors to HTTP.
2. `report_service.generate_report()` reads and cleans the workbook, extracts
   scenarios, validates both chains, and builds IV/EV delta pairs once.
3. For every metric in `REPORT_METRICS`, `report_service.py` selects the IV or
   EV chain according to `metric.chain_kind`.
4. `report_builder.build_metric_report()` creates monthly base/final tables,
   yearly delta tables, and machine-yearly delta tables.
5. The route maps the result into explicit Pydantic response fields.

`POST /reports/data-preview` uses the same metric definitions but calls
`build_metric_preview()`, which returns monthly base/final tables and monthly
delta tables for dashboard rendering.

Excel export uses `REPORT_METRICS` in `backend/excel/report_writer.py` to write
the three sheets per metric:

- `<excel_prefix>_month`
- `<excel_prefix>_sheet`
- `<excel_prefix>_machine_sheet`

## Frontend Flow

Frontend metric metadata lives in `frontend/src/reportMetrics.ts`.

`SECTIONS` defines every sidebar/dashboard section and maps it to a
`ReportData` property. `ResultPage.tsx` uses those definitions instead of
hard-coded switch statements. Shared report payload types live in
`frontend/src/types/report.ts`.

The larger table renderers were moved to:

- `frontend/src/components/report/ReportSections.tsx`

`DataPreview.tsx` includes tabs for IV heat and heat production.

## How To Add A New Metric

1. Add the source column constant in `backend/core/constants.py`.
2. Add the column to `METRIC_COLS` so cleaning coerces it to numeric.
3. Add the column to `REQUIRED_DATA_COLS` if the workbook must contain it.
4. Add one `ReportMetric` entry in `backend/domain/report_metrics.py`.
5. Add explicit fields to `DataPreviewResponse` and `GenerateReportResponse` in
   `backend/api/schemas.py`.
6. Map those fields in `backend/api/routes_reports.py`.
7. Add the corresponding `ReportData` properties in
   `frontend/src/types/report.ts`.
8. Add three `SECTIONS` entries in `frontend/src/reportMetrics.ts`.
9. Map API snake_case fields to camelCase in `ConfigurePage.tsx` and
   `ResultPage.tsx`.
10. Add fixture values in `backend/tests/conftest.py`.
11. Add or extend tests:
    - `backend/tests/unit/test_report_metrics.py` for metadata correctness.
    - `backend/tests/unit/test_report_builder.py` for builder behavior.
    - `backend/tests/unit/test_cleaning.py` for numeric coercion.
    - `backend/tests/unit/test_report_writer.py` for Excel sheet presence.
    - `backend/tests/integration/test_generate_report.py` for API preview,
      generate, and export coverage.

## Ground Truth Notes

In `data/2026-05-13_162752__EG__monthly (DEXTER).xlsx`,
`HEAT_PRODUCTION__GWH` exists but contains only zero values across all
scenarios. The separate `HEAT_COSTS` column is not a report metric and should
not create dashboard sections or Excel output sheets.

## Verification

Backend:

```powershell
conda activate myenv
python -m pytest backend/tests -v
```

Frontend:

```powershell
cd frontend
npm run build
```
