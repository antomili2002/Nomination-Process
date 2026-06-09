# Project Documentation

## Overview

**Nomination Process** is a full-stack internal tool for Uniper that reads a
monthly scenario Excel export, lets analysts configure scenario comparison
chains, and generates an interactive report with delta tables — exactly
matching the ground-truth Excel layout.

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime |
| FastAPI | 0.115+ | REST API framework |
| Uvicorn | latest | ASGI server |
| Pandas | 2.x | Data processing |
| openpyxl | 3.x | Excel reading/writing |
| Pydantic v2 | — | Request/response validation |
| pydantic-settings | — | Environment configuration |
| pytest + httpx | — | Test runner + HTTP test client |

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | 5 | Type safety |
| Vite | 8 | Dev server + bundler |
| HTML5 Drag & Drop API | — | Chain builder UX |

No additional state management library (Redux, Zustand, etc.) is used — the
app is small enough for `useState` / prop-passing.

---

## Architecture

The report pipeline now uses a metric-driven v2 structure. Metric definitions
live in `backend/domain/report_metrics.py`; reusable report construction lives
in `backend/processing/report_builder.py`; frontend section metadata lives in
`frontend/src/reportMetrics.ts`. See
[`report-metrics-v2.md`](report-metrics-v2.md) for the current metric model and
the checklist for adding future reports.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Browser (React + Vite :5173)                                        │
│  UploadPage → ConfigurePage → ResultPage                            │
│  Vite proxy: /api/* → http://localhost:8000/*                       │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP / JSON
┌───────────────────────────▼─────────────────────────────────────────┐
│ FastAPI (Uvicorn :8000)                                             │
│                                                                     │
│  routes_upload.py       POST /upload                                │
│  routes_reports.py      POST /reports/preview-chain                 │
│                         POST /reports/data-preview                  │
│                         POST /reports/generate                      │
│                                                                     │
│  ── services/ ──────────────────────────────────────────────────    │
│  report_service.py      preview_chain()  preview_data()             │
│                         generate_report()                           │
│                                                                     │
│  ── processing/ ────────────────────────────────────────────────    │
│  readers.py             read_workbook_sheets()                      │
│  scenario_extraction.py extract_scenarios()                         │
│  cleaning.py            clean_data()                                │
│  chain_builder.py       build_delta_pairs()  validate_chain()       │
│  monthly_output.py      aggregate_monthly()                         │
│  yearly_delta_output.py compute_yearly_delta()                      │
│  delta_output.py        compute_delta()   (data-preview only)       │
│  pivot.py               to_pivot_table()  (data-preview only)       │
│                                                                     │
│  ── storage/ ───────────────────────────────────────────────────    │
│  temp_files.py          save_upload()  get_upload_path()            │
│                         delete_upload()                             │
│                                                                     │
│  ── core/ ──────────────────────────────────────────────────────    │
│  config.py              Settings (upload_dir, report_dir, CORS)     │
│  constants.py           Column name constants                       │
│  exceptions.py          Domain exception hierarchy                  │
└─────────────────────────────────────────────────────────────────────┘
         │ writes / reads
┌────────▼────────┐
│ backend/tmp/    │
│   uploads/      │  .xlsx files (deleted after generate_report)
│   reports/      │  (reserved for future download endpoint)
└─────────────────┘
```

### Request lifecycle for `/reports/generate`

```
POST /reports/generate
  → routes_reports.generate_report (controller)
    → report_service.generate_report (service)
      → temp_files.get_upload_path     (find file on disk)
      → readers.read_workbook_sheets   (parse xlsx, releases handle immediately)
      → cleaning.clean_data            (normalise columns / dtypes)
      → scenario_extraction._build_index_map
      → chain_builder.validate_chain + build_delta_pairs
      → monthly_output.aggregate_monthly   (per scenario)
      → yearly_delta_output.compute_yearly_delta (per pair)
      → returns plain dict
    → controller maps dict → GenerateReportResponse (Pydantic)
  → BackgroundTask: temp_files.delete_upload
  → HTTP 200 JSON
```

---

## Coding Style Guide

### Python

- **One concern per module.** Processing functions (`processing/`) are pure:
  they accept DataFrames, return DataFrames or dicts, have no side-effects.
- **Controllers are thin.** Routes (`api/`) call exactly one service function,
  catch domain exceptions via `_to_http()`, and map to response schemas.
  No business logic in routes.
- **Services coordinate.** `services/report_service.py` orchestrates calls to
  multiple processing functions and returns plain Python dicts. Metric-specific
  behavior belongs in `domain/report_metrics.py` and `processing/report_builder.py`,
  not in the service layer.
- **No magic strings.** All column names live in `core/constants.py`.
  Report field names, chain ownership, and Excel sheet prefixes live in
  `domain/report_metrics.py`.
- **Domain exceptions.** Raise `InvalidWorkbookError`, `InvalidChainError`,
  or `ScenarioExtractionError` from processing functions — never `HTTPException`.
  The controller converts them.
- **Type hints everywhere** on all public function signatures.
- **File handles must be closed.** Always use `with pd.ExcelFile(...) as xl:`.
  On Windows, an unclosed handle locks the file against deletion.

### TypeScript / React

- **Snake_case ↔ camelCase mapping** happens at the API boundary in the
  component that calls `fetch` — internal state always uses camelCase.
- **No state management library.** All shared state lives in `App.tsx` and is
  passed down via props.
- **Inline styles** for component-specific layout; CSS variables
  (`--clr-blue`, `--sp-4`, etc.) for theme tokens.
- **Number formatting** uses `toLocaleString('en-GB', ...)` so thousands
  separators and decimal places match the ground-truth Excel.
- Negative delta values are displayed as `-123.456` in red (`#c0392b`).
  Positive values are in Uniper blue (`var(--clr-blue)`).

---

## Testing

### Structure

```
backend/tests/
  conftest.py          Shared fixtures (sample_workbook_bytes, data_df, …)
  unit/                Pure-function tests (no HTTP, no disk I/O)
    test_chain_builder.py
    test_cleaning.py
    test_delta_output.py
    test_monthly_output.py
    test_report_builder.py
    test_report_metrics.py
    test_readers.py
    test_scenario_extraction.py
    test_yearly_delta_output.py
  integration/         Full HTTP pipeline tests via TestClient
    test_generate_report.py
```

### Running tests

```bash
# From the project root with the conda env active:
python -m pytest -v

# Single file:
python -m pytest backend/tests/unit/test_chain_builder.py -v

# With coverage:
python -m pytest --cov=backend --cov-report=term-missing
```

### Fixture data (conftest.py)

The shared fixture builds a deterministic in-memory `.xlsx` workbook:

| Scenario | Type | Value/row |
|---|---|---|
| Base_IV | INTRINSIC_VALUE | 1 000 |
| Outage_IV | INTRINSIC_VALUE | 1 200 |
| Final_IV | INTRINSIC_VALUE | 1 800 |
| Base_EV | EXTRINSIC_VALUE | 500 |
| Outage_EV | EXTRINSIC_VALUE | 700 |
| Final_EV | EXTRINSIC_VALUE | 1 300 |
| Base_IV | IV_INCL_HEAT_COSTS | 900 |
| Final_IV | IV_INCL_HEAT_COSTS | 1 700 |
| Base_IV | HEAT_PRODUCTION__GWH | 10 |
| Final_IV | HEAT_PRODUCTION__GWH | 18 |

Each scenario has 1 machine × 2 tariffs × 2 months = 4 rows (all in year 2026).
Yearly totals: `value × 4` (e.g. Base_EV = 2 000, Final_EV = 5 200).

### How to add a new unit test

1. Create `backend/tests/unit/test_<module>.py`.
2. Import the function under test and any constants from `backend.core.constants`.
3. Use the session-scoped `data_df` fixture from `conftest.py` for data access.
4. Follow the naming pattern: `test_<what>_<expected_behaviour>`.

```python
# Example skeleton
import pytest
from backend.core.constants import EV_COL
from backend.processing.my_new_module import my_function

def test_returns_correct_value(data_df):
    result = my_function(data_df, EV_COL)
    assert result == pytest.approx(42.0)
```

### How to add a new integration test

Integration tests use `TestClient` from FastAPI and cover the full HTTP stack.

```python
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_my_endpoint(sample_workbook_bytes):
    resp = client.post("/my-endpoint", json={...})
    assert resp.status_code == 200
    assert resp.json()["key"] == "expected"
```

**Important:** `POST /reports/generate` deletes the uploaded file as a
background task. Use a **function-scoped** fixture (default scope) for
`uploaded` in any test that calls this endpoint.

---

## Adding New Functionality

### Backend: new processing function

1. Add a module in `backend/processing/my_feature.py`.
2. Write pure functions: `DataFrame → dict` or `DataFrame → DataFrame`.
3. Add unit tests in `backend/tests/unit/test_my_feature.py`.
4. Expose via the service layer (`report_service.py`) if the feature is part
   of report generation, or create a new service file.

### Backend: new report metric

Use the v2 metric checklist in [`report-metrics-v2.md`](report-metrics-v2.md).
In short: add the column constant, add a `ReportMetric`, expose explicit API
fields, map the frontend `ReportData`, and cover the metric in unit and
integration tests. Do not add another hard-coded block to `report_service.py`.

### Backend: new endpoint

1. Define request/response schemas in `backend/api/schemas.py`.
2. Add a service function in `backend/services/`.
3. Add a route in the relevant `routes_*.py` — keep it to:
   - call service, catch exceptions, return schema.
4. Register the router in `backend/main.py` if it's a new router file.
5. Add integration tests.

### Frontend: new page / step

1. Create `frontend/src/pages/MyPage.tsx`.
2. Add the step to the `AppStep` union type and `STEPS` array in `App.tsx`.
3. Render it in the `App.tsx` switch.
4. Use CSS variables for all colours and spacing.

---

## Running Locally

### Prerequisites

- Python 3.11 in a conda/venv environment with `requirements.txt` installed.
- Node.js 20+ with npm.

### Backend

```bash
# From the project root with conda env active:
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

The Vite dev server proxies `/api/*` → `http://127.0.0.1:8000/*` and strips
the `/api` prefix, so all frontend `fetch('/api/upload')` calls reach FastAPI.

---

## Deployment

### Backend (production)

```bash
# Single worker (small load):
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Multi-worker (recommended):
gunicorn backend.main:app -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:8000
```

Set environment variables (or `.env` file):

```dotenv
UPLOAD_DIR=/data/uploads
REPORT_DIR=/data/reports
CORS_ORIGINS=["https://your-frontend-domain.com"]
MAX_UPLOAD_BYTES=157286400   # 150 MB
```

**Important for multi-worker:** `UPLOAD_DIR` and `REPORT_DIR` must be on a
shared volume (NFS, EFS, or similar) — each worker must be able to read the
file saved by another worker.

### Frontend (production)

```bash
cd frontend
npm run build        # outputs to frontend/dist/
```

Serve `frontend/dist/` with any static host (Nginx, Caddy, S3 + CloudFront,
Vercel, etc.).  Configure the reverse proxy to forward `/api/*` to the
FastAPI server.

**Nginx example snippet:**

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
}
location / {
    root /var/www/nomination-process/dist;
    try_files $uri $uri/ /index.html;
}
```

### Docker (optional)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `UPLOAD_DIR` | `backend/tmp/uploads` | Where uploaded workbooks are stored |
| `REPORT_DIR` | `backend/tmp/reports` | Where generated Excel reports are stored |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `MAX_UPLOAD_BYTES` | `157286400` (150 MB) | Max accepted file size |


---

### Frontend Caching and Filter Optimization
The frontend `ResultPage` includes an optimized local caching mechanism for the machine filter:
- When a user filters by specific `MACHINE_NAME`s, the frontend locally caches the generated report data under a unique key representing the sorted machine selections.
- If the user re-selects a previously generated combination of machines, the frontend will restore the UI instantly from the memory cache instead of requesting a new generation from the backend.
- The UI handles "All Machines" as a distinct state and explicitly disables unchanged applies.

### Excel Export & Formatting
The finalized file export delivers an exact visual match of the anticipated spreadsheet schema:
- **Download Handling:** The backend endpoint seamlessly streams a binary byte response. The frontend intercepts the `Content-Disposition` header to pull exactly named binary blobs without causing browser streaming hangs.
- **Excel Styling & Theming:** Generates a completely static formatted flat-table that mimics Pivot Table aesthetics exactly matching the design prototypes.
  - Generates pristine white workspaces by removing default gridlines via `ws.sheet_view.showGridLines = False`.
  - Implements uniform Hex backgrounds (`C0E6F5`) bridging Global Metadata filters, Header rows, and Grand Totals alongside matching custom bottom borders spanning the matrices.
  - Assigns exactly formatted Fonts: `Aptos Narrow, 11pt`, conditionally assigned `Bold` weight for active metadata, column headers, and scenario categories.
  - Instantiates exact Number Format strings (`#,##0`) explicitly injecting thousands-separators to correct native Excel rendering outputs instead of raw floats.
  - Deploys multi-tier programmatic cell indentation mapping hierarchy natively without whitespace injection and aggressively sets column explicit dimensions (widths) to preclude `#####` text overflowing.
