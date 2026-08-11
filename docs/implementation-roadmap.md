# Implementation Roadmap

This document sequences the work to deliver portfolio-aware reports with native
pivot export. It ties together:

- [portfolio-configuration.md](portfolio-configuration.md)
- [portfolio-metrics-and-calculations.md](portfolio-metrics-and-calculations.md)
- [pivot-export-architecture.md](pivot-export-architecture.md)
- [portfolio-layouts.md](portfolio-layouts.md)
- [value-column-selection.md](value-column-selection.md)
- [frontend-portfolio-ux.md](frontend-portfolio-ux.md)

## Guiding Principles

- **UK output stays byte-compatible.** All new behaviour is gated behind the
  detected portfolio / layout, defaulting to today's path.
- **Additive schema/registry changes.** New metric columns are optional; new
  request fields default to current behaviour when omitted.
- **Ship in vertical slices** so each phase is independently testable.

## Phase 0 — Foundations (backend, no behaviour change)

1. Add new column constants and register the new metrics
   (`backend/core/constants.py`, `backend/domain/report_metrics.py`); add
   `aggregation` and `value_format` fields to `ReportMetric`.
2. Coerce the new numeric columns in `backend/processing/cleaning.py`; keep them
   out of `REQUIRED_DATA_COLS`.
3. Create `backend/domain/portfolios.py` with `PortfolioConfig`, the registry,
   `detect_portfolio()`, and `resolve_selected_metrics()`.

*Exit:* unit tests for detection and metric registration pass; UK behaviour
unchanged.

## Phase 1 — Portfolio detection end-to-end (backend)

4. Detect portfolio during upload
   (`backend/services/upload_service.py`); persist it on the processed-upload
   artifact (`backend/storage/processed_uploads.py`,
   `backend/domain/workbook.py`).
5. Surface `portfolio`, `available_metrics`, `default_metrics` in
   `UploadResponse` (`backend/api/schemas.py`, `backend/api/routes_upload.py`).

*Exit:* `/upload` returns the portfolio for UK/NL/DE/Hydro/Nuclear fixtures.

## Phase 2 — Metric selection + conditional aggregation (backend)

6. Add `selected_metrics`, `as_of_date`, `delta_labels` to preview/generate/
   export schemas; validate against the portfolio.
7. Iterate resolved metrics (not all `REPORT_METRICS`) in
   `report_service` / `report_builder`.
8. Make peak/offpeak conditional in `backend/processing/monthly_output.py`
   (drop `TARIFF` from group keys for non-UK portfolios).

*Exit:* preview/generate honour the selected metrics and suppress tariff for
non-UK; UK regression green.

## Phase 3 — Native pivot export (backend)

9. Add `openpyxl` to `requirements.txt`.
10. Author template workbooks under `backend/excel/templates/` per portfolio +
    view, following the checklist in
    [portfolio-layouts.md](portfolio-layouts.md).
11. Implement `backend/processing/report_builder.build_pivot_source()` →
    long-format frame including labelled delta members and `Delta %`.
12. Implement `backend/excel/pivot_export.py` (load template, write `Data` +
    `Info`, set filters + `refreshOnLoad`, return bytes).
13. Branch in `backend/services/download_service.py` on `PortfolioConfig.layout`
    (`UK_CLASSIC → report_writer`, `PIVOT → pivot_export`).

*Exit:* NL/DE/Hydro/Nuclear exports open in Excel without repair and pivots
match the screenshots after on-open refresh; UK export unchanged.

## Phase 4 — Frontend (portfolio-aware UI)

14. Upload page: show detected portfolio + override; store metric metadata.
15. Configure page: value-column checkboxes, per-step delta-label inputs,
    as-of-date input.
16. `reportMetrics.ts`: derive sections from portfolio + selection; add new NL
    metric definitions.
17. Result page: dynamic sections, hide tariff for non-UK, send new fields on
    download. Replace hard-coded `Header` label.

*Exit:* full flow works per portfolio; UK visually unchanged.

## Phase 5 — Hardening

18. Add fixtures for each portfolio under `backend/tests/fixtures/` and
    integration tests through `/upload` → `/generate` → `/export`.
19. Pivot round-trip regression test (reopen export, assert pivot parts +
    `refreshOnLoad`).
20. Document the verified `openpyxl` version pin and any template-authoring
    notes.

## Dependencies Between Phases

```text
Phase 0 ─► Phase 1 ─► Phase 2 ─► Phase 3 ─► Phase 4 ─► Phase 5
                         └────────────────────────────┘ (frontend can start
                                                          against Phase 2 API)
```

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| openpyxl drops pivot caches on save | Pin a known-good version; round-trip regression test; templates pre-built (not generated) |
| Excel "repair" prompt on open | Keep pivots in templates; only replace source data + resize table; validate manually per portfolio |
| Custom labelled deltas not expressible as native drag fields | Hybrid model: raw scenarios as fields **plus** pre-computed labelled delta members (see [pivot-export-architecture.md](pivot-export-architecture.md)) |
| Portfolio mis-detection for Hydro/Nuclear | `MARKET_AREA` → name-pattern fallback → UI override |
| `FUEL_POS_TOT__UOM` summed by mistake | `aggregation="none"`; carried as label, excluded from value fields |
| Large `Data` source slows export | Reuse `ReportAggregationCache`; write long frame once; stream save |

## Open Items (carried from other docs)

1. Confirm whether an upload can mix portfolios (assumed: one per upload).
2. Hydro IV currency vs. plain formatting.
3. Exact monthly range (1–12 vs. from current month).
4. Whether `Delta %` is needed beyond NL.
5. Final method for `Delta %` in pivots (pre-computed member vs. *Show Values As*).
