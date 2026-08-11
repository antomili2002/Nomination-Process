# Value Column Selection

This document specifies the feature that lets the user **choose which value
columns (metrics) appear** in a report, per portfolio. The selection starts from
the portfolio defaults and is refined by the user on the Configure page; it
flows through preview, generation, and the native-pivot export.

Related: [portfolio-configuration.md](portfolio-configuration.md),
[portfolio-metrics-and-calculations.md](portfolio-metrics-and-calculations.md),
[frontend-portfolio-ux.md](frontend-portfolio-ux.md).

## Behaviour

- On reaching **Configure**, the metric checkboxes are **pre-filled with the
  portfolio's `default_metric_keys`**.
- The portfolio's `optional_metric_keys` are shown **unchecked** (e.g. the NL
  extras: Adjusted Running Regime, Sum of Starts, Heat Costs, Fuel Position GJ,
  Fuel Position UoM, Fuel Cost Elec, CO₂ Cost Elec).
- The user can add/remove any available metric. At least one must remain
  selected.
- The selection determines:
  - which `Sum of …` row groups appear in each pivot view,
  - which value fields exist in the exported `Data` source,
  - which sections render on the Result page.

## Data Flow

```text
UploadResponse(portfolio, available_metrics, default_metrics)
        │
        ▼
Configure page  ──(selected_metrics[])──►  POST /reports/data-preview
        │                                    POST /reports/generate
        │                                    POST /reports/export
        ▼
report_service filters REPORT_METRICS by selected_metrics
        ▼
report_builder builds only the selected metrics
        ▼
pivot_export emits value fields / row groups only for selected metrics
```

## API Changes

Add `selected_metrics: list[str] | None` to the preview, generate, and export
request bodies (`backend/api/schemas.py`). Semantics:

- `None` → use the portfolio defaults (backward compatible).
- non-empty list → use exactly these metric keys (validated against the
  portfolio's available set).

`UploadResponse` gains:

- `portfolio: str`
- `available_metrics: list[MetricOption]` (`{key, label, format, optional}`)
- `default_metrics: list[str]`

Validation (in the service, mapped to HTTP 400):

- every requested key exists in the metric registry,
- every requested key is allowed for the detected portfolio
  (`default_metric_keys ∪ optional_metric_keys`),
- the list is non-empty after resolution.

## Backend Filtering

`report_service.generate_report_from_workbook()` and the preview path currently
iterate `REPORT_METRICS`. They change to iterate the **resolved** metric list:

```python
resolved = resolve_selected_metrics(portfolio, request.selected_metrics)
for metric in resolved:
    ...
```

`resolve_selected_metrics` lives next to the portfolio registry and returns the
ordered tuple of `ReportMetric` objects (defaults order preserved). The
`ReportAggregationCache` keys already include the metric column, so caching
remains correct when the selection changes between requests.

## Export

`pivot_export.build_pivot_source()` includes only the selected metrics in the
long-format `METRIC` dimension, so the pre-built pivots naturally render only the
chosen `Sum of …` groups (empty groups collapse). No template change is needed
per selection — the template references all possible metrics, and absent metrics
simply contribute no rows.

## Frontend

See [frontend-portfolio-ux.md](frontend-portfolio-ux.md) for the checkbox UI,
defaults, and how the selection is sent with each request. The Result-page
section list is derived from the selection so users never see empty sections.

## Touch Points

| Concern | File |
|---|---|
| Request/response schemas | `backend/api/schemas.py` |
| Resolution + validation | `backend/domain/portfolios.py`, `backend/services/report_service.py` |
| Metric iteration | `backend/services/report_service.py`, `backend/processing/report_builder.py` |
| Export source | `backend/excel/pivot_export.py` |
| UI selection | `frontend/src/pages/ConfigurePage.tsx`, `frontend/src/reportMetrics.ts` |

## Verification

- Default selection equals the portfolio defaults when `selected_metrics` is
  `None`.
- Requesting an optional NL metric adds exactly that row group to the pivots and
  the matching section to the Result page.
- Requesting a metric not allowed for the portfolio returns HTTP 400.
- Empty selection is rejected.
