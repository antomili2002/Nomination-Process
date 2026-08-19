# Developer Onboarding

Start here. This project generates **scenario delta reports** from Dexter energy-trading
Excel workbooks: a FastAPI backend parses/aggregates the data and produces both a JSON
report and an Excel export; a React UI drives upload, configuration, and review.

## Read these first

- **[backend-guide.md](backend-guide.md)** — FastAPI backend: architecture, upload &
  report pipelines, workbook persistence, Excel export, tests, and how to extend it.
- **[frontend-guide.md](frontend-guide.md)** — React + TypeScript UI: the 3-step
  wizard, state flow, table rendering (UK vs non-UK), and how to extend it.

## The 60-second mental model

```
Excel upload ─▶ backend: read → clean → extract scenarios → detect country/metrics → persist
                          │
   configure chains ─────▶ POST /reports/generate ─▶ report dict (layout: uk | non_uk)
                          │                                 │
                          ├─▶ JSON to React (render tables) │
                          └─▶ POST /reports/export ─▶ xlsxwriter ─▶ .xlsx download
```

- **UK layout:** per-metric monthly pivot + yearly-delta tables, peak/offpeak rows.
- **Non-UK layout** (`UNIT_COUNTRY` ≠ UK): four consolidated views
  (`IV_Yearly`, `IV_Monthly`, `EV_Yearly`, `EV_Monthly`), metrics grouped by category,
  dynamic scenario + delta columns, tariff summed away.

## Run it locally

Backend (from repo root):
```powershell
C:/Users/A03531/AppData/Local/miniconda3/envs/myenv/python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
Frontend (from `frontend/`):
```powershell
npm install; npm run dev      # http://localhost:5173, proxies /api → :8000
```

## Validate changes

```powershell
# backend tests (from repo root)
C:/Users/A03531/AppData/Local/miniconda3/envs/myenv/python.exe -m pytest backend/tests/ -q
# frontend typecheck (from frontend/)
npx tsc --noEmit -p tsconfig.app.json
```

## Other design notes in this folder

- [interactive-pivot-export-plan.md](interactive-pivot-export-plan.md) — research +
  plan for exporting **native, interactive Excel PivotTables** (additive; leaves the
  current static export unchanged).

`architecture-performance-refactor.md` and `deployment.md` capture historical design
decisions; the two guides above reflect the **current** implementation.
