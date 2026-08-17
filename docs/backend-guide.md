# Backend Developer Guide — Scenario Delta Report API

> A complete onboarding reference for the Python / FastAPI backend.
> After reading this you should be able to run, understand, extend, and test the
> whole backend without any other context.

---

## 1. What the backend does

The backend turns an uploaded **Dexter scenario Excel workbook** into structured
**delta reports** that compare energy-trading scenarios (Intrinsic Value, Extrinsic
Value, Power Position, heat metrics, and any other numeric column found in the file).

Two report **layouts** are produced depending on the portfolio:

| Layout    | Trigger                              | Shape |
|-----------|--------------------------------------|-------|
| `uk`      | `UNIT_COUNTRY` absent/blank or `UK`  | One monthly pivot + one yearly-delta table **per metric**, tariff (peak/offpeak) rows preserved. |
| `non_uk`  | `UNIT_COUNTRY` present and not `UK`  | Four consolidated views (`IV_Yearly`, `IV_Monthly`, `EV_Yearly`, `EV_Monthly`), metrics grouped by category, tariff summed away, dynamic scenario + delta columns. |

The same report dict feeds both the JSON API (React frontend) and the Excel exporter.

---

## 2. Tech stack

| Concern        | Choice |
|----------------|--------|
| Web framework  | FastAPI (`backend/main.py`) |
| Validation     | Pydantic v2 (`backend/api/schemas.py`) |
| Data engine    | pandas |
| Excel read     | `openpyxl` (`.xlsx` / OOXML), `python-calamine` (legacy OLE `.xls`) |
| Excel write    | `xlsxwriter` |
| Settings       | `pydantic-settings` (`backend/core/config.py`) |
| Tests          | pytest (+ `httpx`/`TestClient` for integration) |
| Logging        | loguru / stdlib logging |

Python: **conda env `myenv`, 3.11**. Interpreter path used throughout:
`C:/Users/A03531/AppData/Local/miniconda3/envs/myenv/python.exe`.

---

## 3. Directory layout & responsibilities

```
backend/
├── main.py                     # FastAPI app, CORS, background upload cleanup, /healthz
├── api/                        # HTTP adapters only — NO business logic
│   ├── routes_upload.py        # POST /upload
│   ├── routes_reports.py       # POST /reports/preview-chain | /data-preview | /generate
│   ├── routes_download.py      # POST /reports/export
│   └── schemas.py              # All Pydantic request/response models
├── core/                       # Cross-cutting constants & config
│   ├── config.py               # Settings singleton (dirs, TTLs, size limits, CORS)
│   ├── constants.py            # Excel column names + dimension/metric/required sets
│   └── exceptions.py           # 5 domain exceptions -> HTTP status codes
├── domain/                     # Frozen dataclasses (data, no behaviour)
│   ├── workbook.py             # ScenarioInfo, UploadedWorkbook, WorkbookData
│   └── report_metrics.py       # ReportMetric, curated metrics, dynamic discovery
├── services/                   # Orchestrators (coordinate processing + storage)
│   ├── upload_service.py       # process_upload(): read→clean→detect→persist
│   ├── report_service.py       # preview/generate report dicts (UK vs non-UK)
│   └── download_service.py     # create_excel_report(): generate + write .xlsx
├── processing/                 # Pure data transforms (no I/O, no HTTP)
│   ├── readers.py              # read_workbook_sheets(): engine + encryption detection
│   ├── cleaning.py             # clean_data(): validate, trim, coerce numbers
│   ├── scenario_extraction.py  # extract_scenarios(): parse the Info sheet
│   ├── chain_builder.py        # validate_chain(), build_delta_pairs()
│   ├── monthly_output.py       # aggregate_monthly(): groupby scenario/tariff/year/month
│   ├── pivot.py                # to_pivot_table(): tidy -> month-aligned pivot dict
│   ├── delta_output.py         # compute_delta(): per-cell monthly deltas (preview)
│   ├── yearly_delta_output.py  # compute_yearly_delta(): per-year totals + delta
│   └── report_builder.py       # build_metric_*() + build_non_uk_category_sections()
├── storage/                    # File I/O layer
│   ├── temp_files.py           # save_upload(), cleanup_stale_uploads(), report paths
│   └── processed_uploads.py    # save/load_workbook_data(): pickle + json artifacts
├── excel/
│   └── report_writer.py        # write_report(): UK sheets + 4 non-UK sheets
└── tests/                      # pytest suite (unit + integration + conftest fixtures)
```

**Layering rule (SOLID / dependency direction):**
`api → services → processing/domain/storage → core`.
`processing` never imports `api` or `services`. Controllers contain no logic; they
validate input, call a service, and map the returned plain dict to a schema.

---

## 4. Configuration — `core/config.py`

```python
class Settings(BaseSettings):
    upload_dir: Path = Path("backend/tmp/uploads")
    report_dir: Path = Path("backend/tmp/reports")
    cors_origins: list[str] = ["http://localhost:5173"]
    max_upload_bytes: int = 150 * 1024 * 1024        # 150 MB
    upload_ttl_seconds: int = 4 * 3600               # 4 hours
    upload_cleanup_interval_seconds: int = 15 * 60   # 15 minutes
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()   # import this singleton everywhere
```

Any field can be overridden via environment variable or `.env` (e.g. `UPLOAD_DIR=...`).

---

## 5. Constants — `core/constants.py`

```python
# Data-sheet column names (exact strings expected in the Excel "Data" sheet)
SCENARIO_ID_COL   = "SCENARIO_ID"
SCENARIO_NAME_COL = "SCENARIO_NAME"
OUTPUT_TYPE_COL   = "OUTPUT_TYPE"
YEAR_COL          = "YEAR"
MONTH_COL         = "MONTH"
TARIFF_COL        = "TARIFF"
MACHINE_NAME_COL  = "MACHINE_NAME"
UNIT_COUNTRY_COL  = "UNIT_COUNTRY"          # optional; drives layout selection
POWER_POS_COL     = "POWER_POS__GWH"
IV_COL            = "INTRINSIC_VALUE__CUR"
EV_COL            = "EXTRINSIC_VALUE"
IV_INCL_HEAT_COSTS_COL = "IV_INCL_HEAT_COSTS"
HEAT_PRODUCTION_COL    = "HEAT_PRODUCTION__GWH"

METRIC_COLS    = [POWER_POS_COL, IV_COL, EV_COL, IV_INCL_HEAT_COSTS_COL, HEAT_PRODUCTION_COL]
DIMENSION_COLS = [SCENARIO_ID_COL, SCENARIO_NAME_COL, OUTPUT_TYPE_COL, YEAR_COL,
                  MONTH_COL, TARIFF_COL, MACHINE_NAME_COL, UNIT_COUNTRY_COL]

# UNIT_COUNTRY is a dimension but NOT required (legacy UK files omit it)
REQUIRED_DATA_COLS = [c for c in DIMENSION_COLS if c != UNIT_COUNTRY_COL] + METRIC_COLS

# Info-sheet parsing
INFO_HEADER_SENTINEL   = "Scenario Name"    # row containing this = header row
INFO_COL_SCENARIO_NAME = "Scenario Name"
INFO_COL_MARKET_AREA   = "Market Area"
INFO_COL_SCENARIO_TYPE = "Scenario Type"
INFO_COL_STATUS        = "Status"
INFO_COL_SCENARIO_ID   = "Scenario ID"
```

> **Key distinction:** `DIMENSION_COLS` are identity/grouping columns and are never
> offered as selectable metrics. Any *other* numeric column is auto-discovered as a
> dynamic metric (see §8).

---

## 6. Exceptions — `core/exceptions.py` → HTTP mapping

| Exception                | Raised by                                   | HTTP |
|--------------------------|---------------------------------------------|------|
| `InvalidUploadError`     | `temp_files.save_upload` (bad ext / too big) | 400 |
| `InvalidWorkbookError`   | `readers` (missing sheets, encrypted), `cleaning` (missing cols) | 422 |
| `ScenarioExtractionError`| `scenario_extraction` (no header / no rows) | 422 |
| `InvalidChainError`      | `chain_builder.validate_chain`              | 422 |
| `ReportGenerationError`  | report building (catch-all)                 | 500 |

Controllers translate these in a small `_to_http()` helper. `FileNotFoundError`
(unknown/expired `upload_id`) maps to **404**.

---

## 7. HTTP API reference

Base app: `FastAPI(title="Scenario Delta Report API", version="0.1.0")`.
CORS allows `http://localhost:5173`. A background task deletes uploads older than
the TTL every 15 min (started/stopped by the `lifespan` context manager).

### `GET /healthz`
Returns `{"status": "ok"}`.

### `POST /upload`  → `UploadResponse`
Multipart file field `file`. Only `.xlsx` accepted (by name; content is
signature-checked). Calls `upload_service.process_upload`.

```jsonc
UploadResponse {
  upload_id: str,
  file_name: str,
  portfolio_country: str,          // "UK" | detected country
  as_of_date: str | null,          // ISO date from AS_OF_DATE column (upload-time only)
  scenarios: ScenarioInfoRow[],    // index, scenario_name, scenario_id, market_area, scenario_type, status, role
  machines: str[],                 // sorted unique MACHINE_NAME
  available_metrics: MetricInfo[]  // key, label, column, category, default_selected
}
```

### `POST /reports/preview-chain`  → `ChainPreviewResponse`
Validates IV/EV chains and returns the delta pairs that *would* be computed
(`iv_pairs`, `ev_pairs` of `DeltaPairInfo`). Used by the configure screen.

### `POST /reports/data-preview`  → `DataPreviewResponse`
Live preview for the **curated 5 metrics only**. Returns `available_machines`
plus `<metric>_monthly` / `<metric>_deltas` `PivotTable` lists for
`ev, iv, pp, iv_heat, heat_prod`. Honors `selected_machines`.

### `POST /reports/generate`  → `GenerateReportResponse`
The main endpoint. Request:
```jsonc
ReportGenerationRequest {
  upload_id: str,
  iv_chain: int[],                 // >= 2 scenario indices, ordered base..final
  ev_chain: int[],                 // >= 2
  selected_machines: str[] | null, // null = all machines summed
  selected_metrics: str[] | null   // metric keys; null = all available
}
```
Response:
```jsonc
GenerateReportResponse {
  report_id: str,
  upload_id: str,
  portfolio_country: str,
  layout: "uk" | "non_uk",
  metrics: MetricReportSection[],        // populated for UK only
  non_uk_sections: NonUkReportSection[]  // populated for non-UK only
}
```

### `POST /reports/export`  → binary `.xlsx`
Same request body as generate. Streams the workbook with
`Content-Disposition: attachment; filename="scenario_report_YYYYMMDD_HHMMSS.xlsx"`.
The file is built in-memory and streamed — it is **not** written to `report_dir`.

---

## 8. Upload workflow (step by step)

Entry: `POST /upload` → `upload_service.process_upload(file)`.

1. **Save & size-guard** — `storage/temp_files.save_upload`
   - `_validate_extension` rejects anything not ending `.xlsx` → `InvalidUploadError`.
   - New `upload_id = uuid4()`; streams to `backend/tmp/uploads/<upload_id>/<filename>`
     in 256 KB chunks; aborts over `max_upload_bytes` (150 MB).

2. **Read sheets** — `processing/readers.read_workbook_sheets`
   - `_workbook_engine(path)` inspects the first 8 bytes:
     - `50 4B 03 04` (`PK..`, a ZIP) → engine `openpyxl` (normal `.xlsx`).
     - `D0 CF 11 E0 A1 B1 1A E1` (OLE Compound File) → engine `calamine` (legacy `.xls`).
   - `_is_password_protected_workbook(path)` scans for the `EncryptedPackage`
     UTF-16 marker; if found → `InvalidWorkbookError("Password-protected workbooks…")`.
   - Requires both `Info` and `Data` sheets. `Info` is parsed with `header=None`
     (real header row varies); `Data` with a header row.

3. **Clean + extract scenarios (parallel)** — `_process_workbook_frames`
   runs `extract_scenarios` and `clean_data` in a 2-worker `ThreadPoolExecutor`.

   - `cleaning.clean_data`: strip column names → assert `REQUIRED_DATA_COLS`
     (`InvalidWorkbookError` if missing) → trim string dims (incl. `UNIT_COUNTRY`)
     → coerce `YEAR`/`MONTH` numeric → coerce `METRIC_COLS` + any discovered numeric
     column to float (handles European `1.234,5` decimal-comma).
   - `scenario_extraction.extract_scenarios`: find the row containing
     `"Scenario Name"`; keep rows with a non-blank name and a positive integer
     Scenario ID; emit tidy df (`index, scenario_name, scenario_id, market_area,
     scenario_type, status, role`). Errors → `ScenarioExtractionError`.

4. **Detect metadata** — in `upload_service`
   - `_extract_machines`: sorted unique `MACHINE_NAME`.
   - `detect_portfolio_country`: first non-blank `UNIT_COUNTRY` upper-cased, else `"UK"`.
   - `_extract_as_of_date`: first non-null `AS_OF_DATE` as `YYYY-MM-DD`, else `None`.

5. **Discover metrics** — `domain/report_metrics.available_metrics` (see §9).

6. **Persist** — `storage/processed_uploads.save_workbook_data` writes into the
   upload dir:
   | File | Content |
   |------|---------|
   | `info.pkl` | raw Info df |
   | `raw_data.pkl` | raw Data df |
   | `clean_data.pkl` | cleaned Data df |
   | `scenarios.pkl` | scenario table |
   | `machines.json` | machine list |
   | `portfolio_country.json` | detected country |

   > **Note:** `as_of_date` is **not** persisted — it is returned once at upload
   > time and carried by the frontend. Later `generate`/`export` calls reload only
   > the six artifacts above via `load_workbook_data` (missing files → `FileNotFoundError` → 404).

7. **Respond** — `routes_upload._to_response` maps `UploadedWorkbook` → `UploadResponse`.

---

## 9. Metrics — `domain/report_metrics.py`

```python
@dataclass(frozen=True)
class ReportMetric:
    key: str            # unique id ("iv", "ev", "pp", … or the raw column name)
    column: str         # actual Data-sheet column
    label: str          # display label
    output_type: str    # "IV" | "EV"
    chain_kind: str     # "iv" | "ev" — which chain aggregates it
    excel_prefix: str   # sheet-name prefix (<= 20 chars, Excel-safe)
    category: str       # UI grouping
    default_selected: bool
```

**Curated metrics** (`REPORT_METRICS`, category *Core Value Metrics*):

| key | column | label | output | default |
|-----|--------|-------|--------|---------|
| `ev` | EXTRINSIC_VALUE | Extrinsic Value | EV | ✅ |
| `iv` | INTRINSIC_VALUE__CUR | Intrinsic Value | IV | ✅ |
| `pp` | POWER_POS__GWH | Power Position | IV | ✅ |
| `iv_heat` | IV_INCL_HEAT_COSTS | IV incl. heat costs | IV | ❌ |
| `heat_prod` | HEAT_PRODUCTION__GWH | Heat Production | IV | ❌ |

**`available_metrics(data_df)`** returns curated metrics whose column exists and is
numeric, **plus** every other numeric non-dimension column as a *dynamic* metric
(`_build_dynamic_metric`): humanized label, IV chain, not default-selected,
category assigned by keyword rules:

```
Running Regime  ← HOURS/STARTS/AVAILABILITY/CAPACITY
Fuel            ← FUEL
Emissions       ← CO2/SO2/NOX/DUST
Water           ← WATER
Ancillary (FCR) ← FCR
Pricing         ← PRICE/_EUR_/GC_VOLUME/GC_COST
Costs           ← COST
Other Metrics   ← (fallback)
```

---

## 10. Report generation — `services/report_service.py`

`generate_report(...)` loads the workbook then delegates to
`generate_report_from_workbook(...)`, which:

1. Builds `index_to_name` from the scenario table.
2. `validate_chain(iv_chain)` and `validate_chain(ev_chain)` against available indices.
3. `build_delta_pairs(chain, index_to_name)` for each chain (see below).
4. Creates a `ReportAggregationCache` (memoizes `aggregate_monthly` per scenario+metric).
5. Filters `available_metrics` by `selected_metrics`.
6. **Branches on `portfolio_country`:**
   - non-UK → `build_non_uk_category_sections(...)`, `metrics=[]`, `layout="non_uk"`.
   - UK → per-metric `build_metric_report(...)`, `non_uk_sections=[]`, `layout="uk"`.

### Chains & delta pairs — `processing/chain_builder.py`
A chain is an ordered list of scenario indices: `chain[0]` = base, `chain[-1]` =
final. `build_delta_pairs` emits:
- a **step** pair for every consecutive transition (`step_number` 1-based), and
- a **cumulative** pair `base → final` **only when** `len(chain) > 2`.

`validate_chain` rejects chains shorter than 2, with duplicates, or with unknown indices.

### UK per-metric shape — `report_builder.build_metric_report`
```jsonc
{
  "monthly": [ {title, months:[…], rows:[{year, tariff, values:[…]}]},  // base
               {…} ],                                                    // final
  "deltas":  [ {left_name, right_name, pair_type, step_number,
                rows:[{year, left_value, right_value, delta}],
                left_total, right_total, delta_total} ]
}
```
- `monthly` uses only base + final scenarios (`build_monthly_tables`).
- `deltas` are **yearly** aggregates per delta pair (`compute_yearly_delta`).
- `aggregate_monthly` groups by `[SCENARIO_NAME, TARIFF, YEAR, MONTH]`, summing
  machines (all, or the `selected_machines` subset). Tariff (peak/offpeak) stays a row.
- `to_pivot_table` aligns values to the sorted months present and lists `(year,tariff)` rows.

### Non-UK shape — `report_builder.build_non_uk_category_sections`
Groups selected metrics into `IV` (everything except `EXTRINSIC_VALUE`) and `EV`
(only `EXTRINSIC_VALUE`), then by `category`. For each `(output_type, category)` it
emits a **monthly** and a **yearly** section. Columns are dynamic:
```
[ one per chain scenario ]  +  [ "Delta N" per step pair ]  +  [ "Total" if cumulative ]
```
Each row: `{metric_key, metric_label, metric_column, year, month?, values:[…]}`,
where `values` line up with `columns` (scenario sums, then step deltas, then the
cumulative). Tariff is summed away entirely; there are no percentage columns.

---

## 11. Excel export — `services/download_service.py` + `excel/report_writer.py`

`create_excel_report` loads the workbook, calls
`generate_report_from_workbook` (same dict as the API), then
`report_writer.write_report(report_data, info_df, raw_data_df)` returns bytes.

`write_report` opens an `xlsxwriter.Workbook` in `constant_memory` mode, builds a
shared format dictionary (`_create_formats`, base font *Aptos Narrow* 11pt, blue
`#C0E6F5`, number format `#,##0`) and routes by `layout`:

- **UK** — for each metric, two sheets named from a collision-safe
  `excel_prefix`: `<prefix>_month` (`_write_monthly_sheet`, scenario → year →
  tariff hierarchy across 12 month columns + Grand Total) and `<prefix>_sheet`
  (`_write_delta_sheet`, per pair: left/right/dif columns with totals).
- **non-UK** — `_write_non_uk_sheets` creates exactly four sheets
  (`IV_Yearly`, `IV_Monthly`, `EV_Yearly`, `EV_Monthly`) and writes each category
  table into the matching sheet (`Metric | Year | [Month] | scenario cols | delta
  cols | Total …` with a `Total <category>` row).

Finally the raw `Info` and `Data` sheets are appended for traceability
(`_df_to_sheet`).

---

## 12. Storage & lifecycle

- **Uploads** live under `settings.upload_dir/<upload_id>/` (workbook + 6 artifacts).
- **Cleanup**: `cleanup_stale_uploads` deletes upload dirs whose mtime is older than
  `upload_ttl_seconds` (4 h). The `lifespan` task runs it every 15 min; failures are
  swallowed so cleanup can never break request handling.
- **Reports** are streamed in-memory; `report_dir` and `save_report`/`get_report`
  helpers exist for future persistence but the export path does not use them.

---

## 13. Testing

Config: `pytest.ini` → `testpaths = backend/tests`.

Run everything:
```powershell
Set-Location C:\Users\A03531\nomination_process
C:/Users/A03531/AppData/Local/miniconda3/envs/myenv/python.exe -m pytest backend/tests/ -q
```
Run one file / test:
```powershell
… -m pytest backend/tests/unit/test_report_writer.py -q
… -m pytest backend/tests/unit/test_readers.py::test_routes_ole_compound_workbook_to_calamine_reader -q
```

Structure:
```
backend/tests/
├── conftest.py                 # session fixtures: sample_workbook_bytes/_path, info_df, data_df
├── integration/
│   └── test_generate_report.py # full HTTP pipeline via TestClient (upload→generate→export, UK & non-UK)
└── unit/                       # readers, cleaning, scenario_extraction, chain_builder,
                                # monthly_output, pivot, delta_output, yearly_delta_output,
                                # report_builder, report_metrics, report_service_processed_uploads,
                                # report_writer, upload_service, upload_cleanup, processed_uploads, health
```

The `conftest` fixtures build a synthetic workbook with **deterministic values**
(e.g. EV base 500 / final 1300, IV base 1000 / final 1800) so aggregation and delta
maths are asserted exactly.

**Rule of thumb:** every behaviour change ships with a test that would fail without
it. Fix the producer of a wrong value, not the symptom downstream.

---

## 14. How to add new functionality

### Add a new selectable metric
- If it is just a numeric Data column, **nothing to do** — it is auto-discovered.
  Optionally add a keyword to `_CATEGORY_RULES` for nicer grouping.
- To curate it (custom label / default-selected / EV chain), append a `ReportMetric`
  to `REPORT_METRICS` in `domain/report_metrics.py`. Add a `report_metrics` test.

### Add a new API endpoint
1. Add request/response models in `api/schemas.py`.
2. Add a service function in the relevant `services/*.py` returning a plain dict.
3. Add a thin controller in the matching `api/routes_*.py`, mapping domain
   exceptions via `_to_http`.
4. Cover it with a unit test (service) and/or integration test (TestClient).

### Change a report layout / add columns
- Backend row/column shape lives in `processing/report_builder.py`
  (`build_metric_report` for UK, `build_non_uk_category_sections` for non-UK).
- Keep the API dict keys stable, or update `api/schemas.py`, `routes_reports.py`,
  the Excel writer, **and** the frontend types together.
- Mirror any column/row changes in `excel/report_writer.py` and add a writer test.

### Support a new input file format
- Extend `_workbook_engine` / signature handling in `processing/readers.py` and add
  a `test_readers.py` case with the new signature.

### Add a new portfolio layout
- Add a branch in `generate_report_from_workbook`, a new `build_*` in
  `report_builder.py`, a new writer branch, matching schemas, and frontend rendering.

---

## 15. Running the backend locally

```powershell
Set-Location C:\Users\A03531\nomination_process
C:/Users/A03531/AppData/Local/miniconda3/envs/myenv/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/healthz`
- The frontend dev server proxies `/api/*` → `http://127.0.0.1:8000`.

Dependencies: `pip install -r requirements.txt` (FastAPI, uvicorn, pandas, numpy,
openpyxl, **python-calamine**, xlsxwriter, pydantic(-settings), python-multipart,
httpx, pytest, loguru).
