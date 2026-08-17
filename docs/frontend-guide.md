# Frontend Developer Guide — Scenario Delta Report UI

> A complete onboarding reference for the React + TypeScript + Vite frontend.
> After reading this you should be able to run, understand, extend, and test the
> whole UI without any other context.

---

## 1. What the frontend does

A three-step wizard that lets a trader:

1. **Upload** a Dexter scenario Excel workbook.
2. **Configure** the report — order scenarios into IV/EV comparison *chains* and pick
   which metrics to include.
3. **Review** the resulting delta tables, filter by machine, and download the Excel
   report.

The UI adapts to the backend `layout` field: **UK** portfolios get per-metric
monthly + yearly-delta tables (with peak/offpeak tariff rows); **non-UK** portfolios
get consolidated IV/EV category tables with a Monthly/Yearly toggle.

---

## 2. Tech stack & tooling

| Concern      | Choice |
|--------------|--------|
| Framework    | React 19 + TypeScript |
| Build/dev    | Vite (dev server on **5173**, proxies `/api/*` → `http://127.0.0.1:8000`) |
| HTTP         | native `fetch` via `buildApiUrl()` (axios/react-query are installed but unused) |
| Icons        | `lucide-react` (`Download`, `FilePlus2`, `SlidersHorizontal`) |
| Styling      | plain CSS design tokens (`index.css`, `App.css`) + inline styles |
| Tests        | Node's built-in `node:test` runner |

### Commands (run from `frontend/`)
```powershell
npm install                                 # install deps
npm run dev                                 # dev server @ http://localhost:5173
npx tsc --noEmit -p tsconfig.app.json       # typecheck (used as the gate in this repo)
npm run build                               # tsc -b + vite build -> dist/
npm run lint                                # eslint .
npm run preview                             # serve dist/ locally
node --test tests/**/*.test.ts              # run unit tests (scenarioChains)
```

---

## 3. Directory layout

```
frontend/
├── index.html                 # mounts #root
├── vite.config.ts             # dev server + /api proxy
├── tsconfig*.json             # strict TS (noUnusedLocals/Parameters)
├── eslint.config.js           # flat config (JS/TS/react-hooks/react-refresh)
├── package.json               # scripts + deps
├── tests/
│   └── scenarioChains.test.ts # unit tests for chain ordering
└── src/
    ├── main.tsx               # React root (StrictMode)
    ├── App.tsx                # step state machine + UploadContext/ScenarioRow types
    ├── api.ts                 # buildApiUrl()
    ├── index.css / App.css    # design tokens + component styles
    ├── reportMetrics.ts       # UK sidebar section helpers
    ├── types/
    │   └── report.ts          # every backend response interface
    ├── pages/
    │   ├── UploadPage.tsx     # step 1
    │   ├── ConfigurePage.tsx  # step 2
    │   ├── ResultPage.tsx     # step 3
    │   └── scenarioChains.ts  # buildInitialChains()
    └── components/
        ├── Header.tsx
        ├── StepIndicator.tsx
        ├── PivotTable.tsx     # used by DataPreview
        ├── DataPreview.tsx    # optional /data-preview inspector
        └── report/
            └── ReportSections.tsx  # ExcelPivotSection, YearlyDeltaSection, NonUkCategorySections
```

---

## 4. App state machine — `src/App.tsx`

```ts
type AppStep = 'upload' | 'configure' | 'result'
```

`App` holds three pieces of state and swaps the page component:

| State | Set when | Consumed by |
|-------|----------|-------------|
| `step` | navigation | which page renders |
| `uploadCtx: UploadContext \| null` | upload succeeds | ConfigurePage |
| `reportData: ReportData \| null` | generate succeeds | ResultPage |

```
UploadPage  --onSuccess(ctx)-->  ConfigurePage  --onSuccess(data)-->  ResultPage
     ^                                                                     |
     +--------------------------- onReset() -------------------------------+
```

### `UploadContext` (App.tsx)
```ts
interface UploadContext {
  uploadId: string
  fileName: string
  portfolioCountry: string
  asOfDate: string | null
  scenarios: ScenarioRow[]
  machines: string[]
  availableMetrics: MetricInfo[]
}
interface ScenarioRow {
  index: number; scenarioName: string; scenarioId: number
  marketArea: string; scenarioType: string; status: string; role: string | null
}
```

### `ReportData` (types/report.ts)
```ts
interface ReportData {
  reportId: string
  uploadId: string
  asOfDate: string | null
  portfolioCountry: string
  layout: 'uk' | 'non_uk'
  ivChain: number[]
  evChain: number[]
  machines: string[]
  selectedMachines: string[] | null   // null = all machines
  selectedMetrics: string[]
  metrics: MetricSection[]            // UK layout only
  nonUkSections: NonUkReportSection[] // non-UK layout only
}
```

---

## 5. Backend response types — `src/types/report.ts`

The backend sends **snake_case**; pages map it to **camelCase** for the top-level
context objects, but nested table payloads (`metrics`, `nonUkSections`) are kept in
their original snake_case shape and consumed directly by the render components.

```ts
interface MetricInfo    { key; label; column; category: string; defaultSelected: boolean }
interface MetricSection { key; label; column: string; monthly: PivotTableData[]; deltas: YearlyDeltaTable[] }

interface YearlyDeltaRow   { year; left_value; right_value; delta: number }
interface YearlyDeltaTable { left_name; right_name; pair_type: string; step_number: number|null;
                             rows: YearlyDeltaRow[]; left_total; right_total; delta_total: number }

interface NonUkReportColumn  { label: string; kind: string }            // 'scenario' | 'delta' | 'cumulative'
interface NonUkReportRow     { metric_key; metric_label; metric_column: string;
                               year: number; month?: number|null; values: number[] }
interface NonUkReportSection { output_type: 'IV'|'EV'; period: 'monthly'|'yearly';
                               category: string; columns: NonUkReportColumn[]; rows: NonUkReportRow[] }
```

`PivotTableData` (from `components/PivotTable.tsx`): `{ title; pair_type?; step_number?;
months: number[]; rows: { year; tariff; values: number[] }[] }`.

> When you add a backend field, add it here first — strict TS will then flag every
> place that must handle it.

---

## 6. API layer — `src/api.ts`

```ts
buildApiUrl(path, base = import.meta.env.VITE_API_BASE_URL ?? '')
```
- No `VITE_API_BASE_URL` → returns `/api{path}` (uses the Vite dev proxy).
- With it set → `{normalizedBase}{path}` for production deployments.

All calls use `fetch` with manual `loading`/`error` state and read `detail` from the
error JSON body. Endpoints used: `POST /upload`, `POST /reports/generate`,
`POST /reports/export`, and (DataPreview) `POST /reports/data-preview`.

---

## 7. Pages

### 7.1 `UploadPage.tsx` — step 1
- Drag-and-drop or click-to-browse zone; `validate(f)` enforces `.xlsx` and ≤ 150 MB.
- `handleUpload()` POSTs multipart `/upload`, then maps the response to
  `UploadContext` (snake→camel) and calls `onSuccess`.
- Shows expected sheet names and the `0_Base_IV` naming convention as hints.

### 7.2 `ConfigurePage.tsx` — step 2
Builds the two comparison chains and the metric selection.

- **State:** `chains: {iv:number[], ev:number[]}`, `selectedMetrics: Set<string>`,
  drag refs (`dragSrc`, `dropTarget`), `loading`, `error`.
- **Chains** are pre-filled by `buildInitialChains(scenarios)` (see §9). Scenarios
  are dragged from the table into an IV or EV drop zone; items can be reordered or
  removed; insertion indicators show the drop position. A chain needs ≥ 2 items.
- **Metrics** render as checkboxes grouped by `category`; defaults come from
  `defaultSelected`; at least one metric is required.
- `handleGenerate()` POSTs `/reports/generate` with
  `{upload_id, iv_chain, ev_chain, selected_machines:null, selected_metrics:[…]}`
  and maps the payload (incl. `asOfDate` carried from `uploadCtx`) into `ReportData`.

### 7.3 `ResultPage.tsx` — step 3
Renders the report and hosts machine filtering + download.

- **Layout branch:** `isNonUk = reportData.layout === 'non_uk'`.
- **Sidebar** (`REPORT TABLES`, shows `As of: <asOfDate>` when present):
  - UK → one group per metric with `Monthly` / `Yearly Deltas` entries and table
    counts (built via `reportMetrics.buildSections`).
  - non-UK → `IV`/`EV` toggle + `Yearly`/`Monthly` toggle
    (`nonUkOutputType`, `nonUkPeriod` state).
- **Machine filter popover:** `pendingSel` set with All/Clear; `applyMachineFilter`
  computes a `selectedMachines` (null when all) and either restores from `cache`
  (a `Map<cacheKey, ReportData>`, pre-seeded with the initial result) or re-POSTs
  `/reports/generate`. This avoids redundant recomputes.
- **Download:** `handleDownload` POSTs `/reports/export` and triggers a blob
  download using the `Content-Disposition` filename.
- **Table area:** UK renders `ExcelPivotSection` (monthly) or `YearlyDeltaSection`
  (yearly) for the active metric; non-UK renders `NonUkCategorySections` filtered to
  the active `output_type` + `period`.

---

## 8. Report rendering — `components/report/ReportSections.tsx`

Shared number formatters:
- `fmtN(v)` / `fmtY(v)` — integer `en-GB`, em-dash for ~0 (thresholds 0.005 / 0.0005).
- `fmtDelta(v)` — colored: negative red `(n)`, positive blue `n`, ~0 em-dash.
- `fmtDif(v)` — like `fmtDelta` but returns empty string for ~0 (used for delta cells).

### `ExcelPivotSection({ tables, isDelta })` (UK monthly)
Recreates the Excel pivot: columns `Year | Tariff | <months…> | Grand Total`.
Per scenario table: a title band, year rows, capitalized tariff rows, a per-table
subtotal, and — when multiple tables — a bottom Grand Total. Delta mode colors cells.

### `YearlyDeltaSection({ tables, metric })` (UK yearly)
Per delta pair: a `PairBadge` (`Step N` / `Cumulative`, `right vs left`), a header
`Row Labels | left | right | Dif of <metric>`, year rows, and a Grand Total row.

### `NonUkCategorySections({ sections })` (non-UK)
Header `Row Labels | <dynamic columns…>` where columns come straight from
`section.columns` (scenario labels, `Delta N`, optional `Total`). Rows are grouped
by metric:
- a blue **`Sum of <metric_column>`** band,
- **monthly** → bold **year** sub-rows (year totals) followed by indented
  `01.MM.YYYY` month rows,
- **yearly** → one row per year,
- then, after *all* metric groups, the **`Total Sum of <metric_column>`** rows are
  listed together at the very bottom (matching the reference pivot). No `%` columns.
Scenario columns use `fmtY`; delta/cumulative columns use `fmtDif` with color.

---

## 9. Sidebar & chain helpers

### `reportMetrics.ts` (UK sidebar)
- `buildSections(metrics)` → two `Section`s per metric (`…::monthly`, `…::deltas`)
  with `tableType: 'monthly' | 'yearlyDelta'`.
- `findMetric(metrics, key)` → the `MetricSection` for rendering.
- `sectionCount(metrics, key, tableType)` → badge count.

### `scenarioChains.ts`
`buildInitialChains(scenarios)` splits scenarios into IV vs EV (by name regex /
`scenarioType`), orders each by numeric `N_` prefix (non-conforming names kept after),
and returns `{ iv, ev }` index arrays. Covered by `tests/scenarioChains.test.ts`.

---

## 10. Supporting components

- **`Header.tsx`** — sticky Uniper-branded header.
- **`StepIndicator.tsx`** — Upload → Configure → Download progress bar (current =
  numbered blue circle, completed = checkmark).
- **`PivotTable.tsx`** — compact pivot renderer with month abbreviations and
  M/k/b shorthand; used by `DataPreview`.
- **`DataPreview.tsx`** — optional inspector calling `/reports/data-preview` with
  tabs for EV/IV/PP/IV-Heat/Heat-Production and a machine selector.

---

## 11. Styling

Design tokens live in `index.css` `:root` (Uniper blue `#0077C8`, borders,
text colors, `--sp-*` spacing, `--text-*` sizes). Reusable classes: `.card`,
`.btn`/`.btn--primary`/`.btn--ghost`/`.btn--sm`, `.badge*`, `.table`,
`.input`/`.select`, `.spinner`. Component-specific and dynamic styles use inline
`style={{…}}` referencing the same `var(--…)` tokens for consistency.

---

## 12. How to add new functionality

### Surface a new backend field
1. Add it to the relevant interface in `types/report.ts`.
2. Map snake→camel in the page that builds the context (`UploadPage`/`ConfigurePage`)
   and thread it through `ResultPage.mapPayload` if it must survive recompute.
3. Render it; run `npx tsc --noEmit -p tsconfig.app.json` — strict TS lists every
   spot that needs updating.

### Add a column to the non-UK tables
The renderer is already data-driven off `section.columns`; typically only the
backend column list changes. Just ensure `values` length matches `columns`.

### Add a new result view / tab
Extend the sidebar toggles in `ResultPage` and add a render branch in the table
area (or a new component in `components/report/`). Keep UK and non-UK paths separate.

### Change API base / deployment
Set `VITE_API_BASE_URL` at build time; otherwise the Vite proxy (`vite.config.ts`)
handles `/api` in development.

---

## 13. End-to-end data flow

```
UploadPage  POST /upload (multipart)
  → UploadContext {uploadId, portfolioCountry, asOfDate, scenarios, machines, availableMetrics}
ConfigurePage  build iv/ev chains + pick metrics  →  POST /reports/generate
  → ReportData {layout, metrics | nonUkSections, chains, selectedMetrics, asOfDate}
ResultPage  render tables
  ├─ machine filter  → cache hit OR POST /reports/generate (selected_machines)
  └─ download        → POST /reports/export → blob → save "scenario_report_*.xlsx"
onReset → back to UploadPage
```

---

## 14. Conventions

- **State:** local `useState`; props for data + callbacks; no global store/context.
- **Fetching:** native `fetch` + `buildApiUrl`; try/catch; surface `detail`.
- **Types:** strict TS, no implicit `any`, unused locals/params are errors — treat
  `npx tsc --noEmit -p tsconfig.app.json` as the CI gate before committing.
- **Immutability:** update chains/sets via new copies (spread / new `Set`).
- **Keep UK behaviour unchanged** when editing non-UK code paths, and vice versa.
