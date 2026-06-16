# Backend Architecture and Performance Refactor

This document describes the backend refactor that separates HTTP routing from
business logic, persists processed upload artifacts, and reduces repeated
work during preview, report generation, and Excel export.

## Architecture Changes

The backend now follows this flow:

```text
Router -> Service -> Storage / Processing -> Domain objects -> API schemas
```

### Upload

Before the refactor, `backend/api/routes_upload.py` handled too many concerns:

- saving the uploaded file
- opening the workbook
- reading `Info` and `Data`
- extracting scenarios
- cleaning data
- extracting machines
- mapping the response

Now the route is only an HTTP adapter:

- `backend/api/routes_upload.py`
  - receives the `UploadFile`
  - calls `upload_service.process_upload()`
  - maps domain exceptions to HTTP status codes
  - converts the domain result to `UploadResponse`

- `backend/services/upload_service.py`
  - coordinates upload persistence, workbook reading, scenario extraction,
    data cleaning, machine extraction, and processed artifact persistence

- `backend/domain/workbook.py`
  - defines the domain objects used between services and storage:
    `ScenarioInfo`, `UploadedWorkbook`, and `WorkbookData`

- `backend/storage/processed_uploads.py`
  - saves and loads processed upload artifacts

### Report Generation

Report generation now loads parsed workbook artifacts instead of reopening the
original Excel workbook for every request.

`backend/services/report_service.py` now:

- loads `WorkbookData` from processed artifact storage
- uses `workbook.scenarios_df` for chain validation and scenario names
- uses `workbook.clean_data_df` for preview and report calculations
- exposes `generate_report_from_workbook()` so export can reuse the same loaded
  workbook data without forcing another storage read

### Excel Export

Excel export now uses the same processed upload artifacts:

- `backend/services/download_service.py` loads `WorkbookData` once
- report tables are computed from `workbook.clean_data_df`
- the original `Info` and raw `Data` sheets are copied from persisted artifacts
- the export path no longer reopens the original `.xlsx` just to copy sheets

The Excel writer remains responsible only for workbook formatting and output:

- `backend/excel/report_writer.py` still creates the downloadable workbook
- it still writes cells with `openpyxl`
- it benefits from faster upstream data preparation, but the cell-writing loop
  itself has not been replaced with a streaming writer

## Persisted Upload Artifacts

On upload, the backend now stores these files inside the upload directory:

```text
backend/tmp/uploads/<upload_id>/
  original-upload.xlsx
  info.pkl
  raw_data.pkl
  clean_data.pkl
  scenarios.pkl
  machines.json
```

The original workbook is still retained for traceability and compatibility.
The `.pkl` artifacts avoid repeated Excel parsing and repeated pandas cleaning.

The periodic upload cleanup flow removes the whole upload directory after the
configured TTL, so processed artifacts are deleted together with the original
workbook. This keeps recomputation and export fast during the active session
while bounding disk usage in production.

## Performance Improvements

### Upload

Upload now does the expensive workbook parse and data cleaning once, then
persists the result. Upload itself still performs the initial parse and clean,
so the first upload request may not feel dramatically faster. The performance
gain appears in every later operation that uses the upload.

### Data Preview

`/reports/data-preview` no longer:

- opens the `.xlsx` file
- reparses `Info`
- reparses `Data`
- cleans the `Data` sheet again

It loads the processed artifacts and computes preview tables from the already
cleaned dataframe.

### Report Generation

`/reports/generate` no longer reparses or recleans the workbook. It also uses a
request-scoped `ReportAggregationCache` in `backend/processing/report_builder.py`.

That cache avoids duplicate aggregation work for:

- monthly scenario/metric aggregates
- machine/year scenario/metric aggregates

This matters because the same scenario and metric are needed by multiple output
tables: monthly tables, yearly deltas, machine deltas, and multiple delta pairs.

### Excel Export

Yes, the caching and performance boost also affect the later Excel export path.

`/reports/export` now benefits from:

- no repeated Excel parse
- no repeated cleaning
- no duplicate raw sheet read
- reuse of the same report-generation aggregation cache

However, the final Excel file creation still uses `openpyxl` and writes cells
into an in-memory workbook. That means the export is faster on the data
preparation side, but very large reports may still spend noticeable time in the
Excel writer itself.

If export is still slow after this refactor, the next optimization target is
`backend/excel/report_writer.py`, especially:

- streaming/write-only workbook mode
- fewer per-cell style assignments
- precomputed reusable style objects
- avoiding unnecessary writes for empty cells

## HTTP Status Behavior

Upload errors are now split more clearly:

- invalid uploaded file, such as non-`.xlsx` or too large: `400`
- invalid workbook structure, such as missing sheets or columns: `422`
- invalid scenario extraction: `422`

This split is implemented with `InvalidUploadError` and `InvalidWorkbookError`.

## How To Check The Changes Step By Step

Run all commands from the repository root.

### 1. Activate the environment

```powershell
conda activate myenv
```

### 2. Run the backend tests

```powershell
python -m pytest backend/tests -q
```

Expected result:

```text
146 passed
```

The current environment may also print warnings about Starlette/httpx and
pytest cache permissions. Those warnings are not caused by this refactor.

### 3. Check upload creates processed artifacts

Start the API:

```powershell
python -m uvicorn backend.main:app --reload
```

Upload a workbook from the frontend or with an API client. After a successful
upload, inspect:

```text
backend/tmp/uploads/<upload_id>/
```

You should see the original workbook plus:

```text
info.pkl
raw_data.pkl
clean_data.pkl
scenarios.pkl
machines.json
```

### 4. Check upload response still matches the frontend contract

Call:

```text
POST /upload
```

The response should still contain:

```json
{
  "upload_id": "...",
  "file_name": "...",
  "scenarios": [],
  "machines": []
}
```

No frontend payload shape changed.

### 5. Check preview uses the same upload

Call:

```text
POST /reports/data-preview
```

Use the `upload_id` returned by upload. The request should return the same
preview fields as before, but it now reads processed artifacts instead of
reopening and cleaning the Excel workbook.

### 6. Check report generation uses the same upload repeatedly

Call:

```text
POST /reports/generate
```

Then call it again with the same `upload_id`, optionally changing
`selected_machines`.

Expected behavior:

- the same upload remains usable
- no new upload is required
- output values match previous behavior

### 7. Check Excel export benefits from the same processed data

Call:

```text
POST /reports/export
```

Expected behavior:

- response content type is an `.xlsx`
- workbook includes generated metric sheets plus `Info` and `Data`
- export does not need to reopen the original uploaded workbook for parsing
- export still spends time writing the final workbook with `openpyxl`

### 8. Optional code-level checks

The regression tests that protect the performance behavior are:

```powershell
python -m pytest backend/tests/unit/test_report_service_processed_uploads.py -q
```

They verify that:

- report generation uses processed artifacts
- export uses processed artifacts
- repeated monthly aggregations are reused
- machine/year aggregations are prepared and reused

The upload boundary tests are:

```powershell
python -m pytest backend/tests/unit/test_upload_service.py backend/tests/unit/test_processed_uploads.py -q
```

They verify that upload processing persists the expected artifacts.
