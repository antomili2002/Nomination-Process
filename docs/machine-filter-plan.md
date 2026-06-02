# Dynamic Machine Filter in the Result Page

## Is it technically possible?

Yes. The data computation already accepts a `selected_machines` parameter that
filters the source DataFrame before aggregation. The existing
`POST /reports/generate` endpoint already wires this through. The only blocker
is that the uploaded workbook is deleted by a background task after the first
generate call, so a second call would fail with 404.

---

## Minimal-change plan

### What needs to change and where

| # | Location | Change | LOC estimate |
|---|----------|--------|---|
| 1 | `backend/api/routes_reports.py` | Remove the `background_tasks.add_task(delete_upload, ...)` line so the file stays on disk | -1 |
| 2 | `backend/main.py` | Add a startup event that deletes upload directories older than 2 h | +10 |
| 3 | `backend/api/schemas.py` | Add `upload_id` field to `GenerateReportResponse` | +1 |
| 4 | `backend/services/report_service.py` | Return `upload_id` in `generate_report` result dict | +1 |
| 5 | `frontend/src/App.tsx` | Add `uploadId`, `ivChain`, `evChain` to `ReportData` interface | +3 |
| 6 | `frontend/src/pages/ConfigurePage.tsx` | Pass those three extra fields in `onSuccess(...)` | +3 |
| 7 | `frontend/src/pages/ResultPage.tsx` | Add Machine button + popover + re-call generate on change | ~60 |

**Total: ~80 lines changed or added across 7 files.**

---

## How it works end-to-end

```
User clicks Machine button
  → selects subset of machines
  → frontend calls POST /reports/generate with same upload_id, iv_chain, ev_chain, selected_machines=[…]
  → backend reads the still-present workbook, recomputes, returns new payload
  → frontend replaces reportData in state → all pivot tables re-render
```

No new endpoint is needed. The existing `/reports/generate` already accepts
`selected_machines` — we just call it a second time.

---

## Key implementation details

### Backend: stop deleting the upload immediately

```python
# routes_reports.py  — remove this line from generate_report:
background_tasks.add_task(delete_upload, body.upload_id)
```

### Backend: return `upload_id` in the response

```python
# schemas.py
class GenerateReportResponse(BaseModel):
    report_id: str
    upload_id: str          # ← add this
    ...

# report_service.py — generate_report() already returns a dict, add:
    "upload_id": upload_id,   # pass the parameter through
```

### Backend: startup TTL cleanup (replaces background task)

```python
# main.py
import time
from pathlib import Path
from backend.core.config import settings

@app.on_event("startup")
def cleanup_stale_uploads() -> None:
    cutoff = time.time() - 2 * 3600   # 2 hours
    for d in settings.upload_dir.iterdir():
        if d.is_dir() and d.stat().st_mtime < cutoff:
            shutil.rmtree(d, ignore_errors=True)
```

### Frontend: store routing context in ReportData

```typescript
// App.tsx — extend ReportData
interface ReportData {
  reportId: string
  uploadId: string          // ← new
  ivChain: number[]         // ← new
  evChain: number[]         // ← new
  ...
}
```

### Frontend: Machine button in ResultPage

```tsx
// ResultPage.tsx — add state + button
const [machines, setMachines] = useState<string[]>([])        // available (from upload)
const [selMachines, setSelMachines] = useState<string[] | null>(null)

async function recompute(sel: string[] | null) {
  const res = await fetch('/api/reports/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      upload_id: reportData.uploadId,
      iv_chain:  reportData.ivChain,
      ev_chain:  reportData.evChain,
      selected_machines: sel,
    }),
  })
  const payload = await res.json()
  // map snake_case → camelCase, call a setter passed from App
  onReportUpdate(mapPayload(payload))
}
```

The `machines` list can either be stored in `ReportData` (pulled from the
original upload response) or fetched lazily with a dedicated endpoint.

---

## How to implement step-by-step

1. Backend (30 min): remove background cleanup, add `upload_id` to response, add startup TTL cleanup.
2. App.tsx (10 min): extend `ReportData`, pass `uploadId/ivChain/evChain` from ConfigurePage.
3. ResultPage.tsx (45 min): add Machine button (can reuse the same chip component from ConfigurePage), call `recompute` on change, show a loading spinner while recomputing.

Total estimated effort: **~1.5 hours**.
