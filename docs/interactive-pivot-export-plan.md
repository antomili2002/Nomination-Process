# Interactive PivotTable Export — Research & Implementation Plan

> Goal: let users download a workbook whose report tables are **native, live Excel
> PivotTables** they can re-pivot, filter, and re-field inside Excel — **without
> changing any existing export logic or the current static layout**. The new
> capability is purely additive: the existing `xlsxwriter` static export stays as
> is; a second "pivot" export is added alongside it.

---

## 1. Why the current writer cannot produce PivotTables

The current exporter ([backend/excel/report_writer.py](../backend/excel/report_writer.py))
uses **`xlsxwriter`**. XlsxWriter writes cells, cell formats, worksheet Tables,
and charts — but it has **no API to create PivotTables** (this is a long-standing,
explicit limitation of the library). It can only produce the pre-formatted static
grids we ship today.

A native PivotTable in an `.xlsx` is not just formatted cells; it is a set of
extra OOXML parts inside the zip:

```
xl/pivotCache/pivotCacheDefinition1.xml   ← fields, source ref, refreshOnLoad
xl/pivotCache/pivotCacheRecords1.xml      ← cached source rows (optional)
xl/pivotTables/pivotTable1.xml            ← row/col/value/filter field layout,
                                            number formats, calculated items
+ relationships (.rels) and [Content_Types].xml entries wiring them together
```

To add real pivots we must produce those parts by one of the routes below.

---

## 2. Options researched

| # | Approach | Pure Python? | Needs Excel installed? | Cross-platform (Linux server)? | Interactivity | Maintenance |
|---|----------|--------------|------------------------|-------------------------------|---------------|-------------|
| A | **Template + `openpyxl` data refresh** | ✅ | ❌ | ✅ | Full (real pivot) | Low–Med (maintain templates) |
| B | Raw OOXML pivot injection | ✅ | ❌ | ✅ | Full | High (hand-written XML) |
| C | COM automation (`pywin32`) | ✅ (Win only) | ✅ | ❌ | Full | Med, but not deployable |

### A. Template + `openpyxl` refresh — **recommended**
Ship a small, hand-built `.xlsx` **template** per layout that already contains a
PivotTable, configured once in Excel, bound to an Excel **Table** (ListObject) on a
hidden data sheet. At export time we:
1. Load the template with `openpyxl`.
2. Overwrite the data-sheet Table rows with this report's tidy source rows.
3. Resize the Table `ref` to the new row count.
4. Set the pivot cache `refreshOnLoad = True`.
5. Save to a bytes buffer and stream it.

When the user opens the file, Excel refreshes the pivot from the new data and shows
it **fully interactive** — they can drag fields, filter, expand/collapse, add
metrics to the layout, etc. `openpyxl` can *load and preserve* an existing pivot and
expose its cache so we can flag a refresh; it does **not** need to build the pivot
from scratch (which it does not officially support). No Excel install required, works
headless, cross-platform.

**Trade-off:** we maintain a handful of template files. That is the only real cost,
and it is small and version-controlled.

### B. Raw OOXML injection — full control, high effort
Generate `pivotCacheDefinition`, `pivotCacheRecords`, `pivotTable` XML and wire the
relationships/content-types ourselves (e.g., post-processing the zip produced by
XlsxWriter). No template files, total control over field layout and calculated
items. But the XML is verbose and brittle; small mistakes trigger Excel's "repair"
prompt. Good as a **fallback/advanced** path if templates become limiting, not for v1.

### C. COM automation (`pywin32`) — powerful but not deployable
`win32com.client` drives a real Excel process (`PivotCaches.Create`,
`PivotTables.Add`, calculated items via the object model). Produces perfect pivots,
but **requires Excel installed on the host and is Windows-only** — unsuitable for a
headless/Linux backend. Useful only for a local developer tool or to **author the
templates** used by Approach A.

**Decision:** implement **Approach A**; keep **B** documented as a future option;
use **C** only locally to build/edit the templates.

---

## 3. Source data shape required by a PivotTable

A pivot reconstructs any layout from a single **tidy/long fact table** — one numeric
measure per row. We therefore feed one flat sheet with these columns:

| Column | Example | Pivot role |
|--------|---------|------------|
| `OUTPUT_TYPE` | `IV` / `EV` | Report filter |
| `MACHINE_NAME` | `TURBINE_A` | Report filter |
| `SCENARIO_LABEL` | `0. Old`, `1. New`, `2. 2nd Mill` | **Column** field |
| `METRIC` | `INTRINSIC_VALUE__CUR`, `POWER_POS__GWH` | **Row** field (top level) |
| `YEAR` | `2026` | **Row** field |
| `MONTH` | `5` (monthly views only) | **Row** field |
| `VALUE` | `4161797.0` | **Values** = `Sum of VALUE` |

With this single `VALUE` measure:
- **Rows** = `METRIC → YEAR → (MONTH)` reproduces the `Sum of <METRIC>` bands and the
  year/month hierarchy of today's layout.
- **Columns** = `SCENARIO_LABEL` reproduces the `0. Old / 1. New / 2. 2nd Mill`
  columns.
- **Deltas** (`Delta 1`, `Delta 2nd Mill`, `Total`) are **PivotTable calculated
  items** on the `SCENARIO_LABEL` field, e.g. `Delta 1 = '1. New' − '0. Old'`. This
  exactly matches the ground-truth Excel pivot (whose delta columns are calculated
  items) and stays **live** when the user re-pivots. Calculated items are authored
  once in the template and preserved by `openpyxl`.

> **Single source of truth:** build this tidy frame from the **same aggregation the
> report service already computes**, so the pivot's numbers are identical to the
> static export. Provide a small flattener that turns the existing report dict
> (`metrics` / `non_uk_sections`) — or the shared `_ChainContext` aggregation — into
> the long rows above. No aggregation logic changes; we only reshape existing values.

---

## 4. Recommended architecture (additive, isolated)

```
backend/excel/
├── report_writer.py        # UNCHANGED — static xlsxwriter export
└── pivot_export.py         # NEW — template-based interactive pivot export
    ├── build_pivot_source_frame(report_data | ctx) -> pd.DataFrame   # tidy rows
    └── write_pivot_report(report_data, info_df, data_df) -> bytes    # openpyxl

backend/excel/templates/    # NEW — version-controlled .xlsx templates
├── pivot_uk.xlsx
├── pivot_non_uk.xlsx       # (or one per IV/EV × monthly/yearly if simpler)
```

- **Service:** add `download_service.create_pivot_excel_report(...)` mirroring the
  existing `create_excel_report(...)` signature; it calls
  `generate_report_from_workbook` (unchanged) then `pivot_export.write_pivot_report`.
- **API:** add either a new endpoint `POST /reports/export-pivot` or a
  `format: "static" | "pivot"` field on the existing `ReportGenerationRequest`
  (default `static`). Controller stays a thin adapter.
- **Frontend:** add a second button next to "Download Excel", e.g. **"Download
  Pivot (.xlsx)"**, hitting the new endpoint. No change to the existing button.

The current static path is untouched; the two exports coexist.

### `write_pivot_report` sketch (Approach A)
```python
from io import BytesIO
from pathlib import Path
from openpyxl import load_workbook

_TEMPLATES = Path(__file__).parent / "templates"

def write_pivot_report(report_data: dict, info_df, data_df) -> bytes:
    template = _TEMPLATES / ("pivot_non_uk.xlsx"
                             if report_data["layout"] == "non_uk"
                             else "pivot_uk.xlsx")
    wb = load_workbook(template)

    rows = build_pivot_source_frame(report_data)      # tidy long rows
    ws = wb["PivotData"]
    _rewrite_table(ws, table_name="tblPivotData", rows=rows)  # clear + write + resize ref

    # Make Excel rebuild the pivot from the refreshed source on open.
    for pivot in wb._pivots:                # loaded pivots
        pivot.cache.refreshOnLoad = True

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

`_rewrite_table` writes the header row + data rows starting at the table's anchor,
clears any leftover rows below, and sets `ws.tables["tblPivotData"].ref` to the new
`A1:<lastcol><lastrow>` range so the pivot cache covers exactly the new data.

---

## 5. What the templates contain (built once, in Excel)

For each template (authored manually or via a local `pywin32` script):
1. A hidden sheet **`PivotData`** with an Excel **Table** named `tblPivotData` whose
   columns are exactly the tidy columns in §3 (one header row, one seed data row).
2. A visible sheet **`Pivot`** with a PivotTable bound to `tblPivotData`, laid out to
   reproduce the current report:
   - Rows: `METRIC`, `YEAR`, (`MONTH` for monthly), Columns: `SCENARIO_LABEL`,
     Values: `Sum of VALUE`.
   - **Calculated items** on `SCENARIO_LABEL` for `Delta 1`, `Delta 2nd Mill`, `Total`.
   - Report filters: `OUTPUT_TYPE`, `MACHINE_NAME`.
   - Number format `#,##0`, the shared blue pivot style, grand totals as configured.
3. `PivotTable options → Data → Refresh data when opening the file` enabled (this is
   the `refreshOnLoad` flag we also force in code as a safety net).
4. Optionally, the raw **`Info`** and **`Data`** reference sheets, matching today's
   export.

Because the layout, styling, and delta definitions live in the template, the export
code only pushes data — guaranteeing the pivot's default view matches the current
static layout while remaining fully editable by the user.

---

## 6. Integration steps (phased, low-risk)

- **Phase 0 — Spike (proof):** hand-build one `pivot_non_uk.xlsx`, wire a throwaway
  script that rewrites `tblPivotData` and sets `refreshOnLoad`, open in Excel, confirm
  the pivot refreshes and is interactive. Decide one-template-with-slicers vs
  one-per-view.
- **Phase 1 — Tidy builder:** implement `build_pivot_source_frame(report_data)` and
  unit-test that its totals equal the static export's `Total Sum of <metric>` values.
- **Phase 2 — Writer + service + API:** add `pivot_export.write_pivot_report`,
  `download_service.create_pivot_excel_report`, and the endpoint/flag. Stream bytes
  with the same `Content-Type`/`Content-Disposition` pattern as
  [routes_download.py](../backend/api/routes_download.py).
- **Phase 3 — Frontend:** add the "Download Pivot" button in
  [ResultPage.tsx](../frontend/src/pages/ResultPage.tsx) hitting the new route.
- **Phase 4 — Deltas as calculated items:** finalize the delta calculated items in the
  templates; verify against the ground-truth pivot columns.
- **Phase 5 — Tests + docs:** see §7; update [backend-guide.md](backend-guide.md).

No existing function is modified; every step adds new code paths.

---

## 7. Testing strategy

- **Unit — tidy builder:** row counts (`metrics × scenarios × years × [months]`) and
  that `Sum of VALUE` per `(METRIC, scenario)` equals the corresponding static
  export total (single source of truth guarantee).
- **Structure — exported file:** load the produced bytes with `openpyxl` and assert:
  - a `PivotData` Table exists with the expected header and the correct `ref`
    dimension for the row count;
  - at least one pivot part is present and its cache has `refreshOnLoad is True`;
  - the reference `Info`/`Data` sheets still match the static export (if included).
- **Golden template test:** commit the template(s) and assert they load/save through
  `openpyxl` without dropping the pivot (guards against `openpyxl` version regressions).
- **Manual acceptance:** open in Excel, confirm the default view matches the static
  layout, then drag a field / add a metric / change a filter to confirm interactivity.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|------|-----------|
| `openpyxl` version drops/corrupts the pivot on save | Pin `openpyxl`; golden-file round-trip test; keep templates minimal. |
| Calculated-item deltas fragile across Excel versions | Author/verify in target Excel; ship a fallback template with scenario columns only if needed. |
| Excel "repair" prompt from malformed parts | Prefer the template route (Excel-authored XML) over hand-written XML (Approach B). |
| Locale number separators (EU dots) | Store plain numbers + `#,##0`; let Excel render per user locale (same as today). |
| Row-count / `ref` mismatch → empty pivot | Always resize `tblPivotData.ref` and force `refreshOnLoad`; assert in tests. |
| Template drift vs. static layout | Keep templates in `backend/excel/templates/` under version control; review with the writer. |

---

## 9. Dependencies

- **No new runtime dependency** for Approach A — `openpyxl` is already installed
  (`3.1.5`) and used by pandas.
- `pywin32` is present in the dev env but is **only** for locally authoring templates
  (Approach C); it must **not** be required by the server path.
- Approach B (raw XML) would also need no new deps but is not planned for v1.

---

## 10. Summary

- XlsxWriter cannot emit PivotTables, so the interactive export is a **separate,
  additive path**.
- **Recommended:** template `.xlsx` files containing pre-built, styled PivotTables
  bound to an Excel Table; the exporter (`openpyxl`) only refreshes the tidy source
  rows and flags `refreshOnLoad`. Pure Python, headless, cross-platform, fully
  interactive for the end user.
- The tidy source is derived from the **existing** report aggregation, so pivot
  numbers and the default layout match today's static export exactly — deltas become
  live PivotTable **calculated items**.
- Existing static export, report logic, and layout remain **unchanged**.
