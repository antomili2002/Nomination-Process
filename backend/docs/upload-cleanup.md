# Upload Cleanup

## Problem

Uploaded workbooks are stored below `backend/tmp/uploads/<upload_id>/`.
The backend intentionally keeps these directories after report generation so
the same `upload_id` can be reused for previews, machine-filter recomputation,
and Excel export without re-uploading or re-parsing the workbook.

Without a cleanup policy, that directory grows indefinitely in production.

## Current Behavior

Upload cleanup is now a TTL-based background task:

1. `backend.storage.temp_files.cleanup_stale_uploads()` owns deletion logic.
2. `backend.main.lifespan()` starts `_periodic_upload_cleanup()` when FastAPI
   starts.
3. The cleanup loop runs once immediately, then sleeps for the configured
   interval.
4. Each sweep deletes only upload directories whose modification time is older
   than `UPLOAD_TTL_SECONDS`.
5. Files directly inside `UPLOAD_DIR` are ignored.
6. Per-directory deletion failures are ignored so one locked or broken folder
   cannot interrupt request handling.

## Configuration

| Setting | Default | Meaning |
|---|---:|---|
| `UPLOAD_TTL_SECONDS` | `14400` | Keep uploads for 4 hours |
| `UPLOAD_CLEANUP_INTERVAL_SECONDS` | `900` | Sweep every 15 minutes |

Example `.env` values for a lower-retention environment:

```dotenv
UPLOAD_TTL_SECONDS=3600
UPLOAD_CLEANUP_INTERVAL_SECONDS=300
```

## Why Not Delete After Report Generation?

Immediate deletion breaks useful reuse:

- Recomputing report data with a different machine filter.
- Exporting an Excel file after a preview/generate step.
- Reusing the processed workbook cache created during upload.

The TTL approach preserves those workflows while still bounding disk usage.

## Step-by-Step Verification

Run the focused tests:

```powershell
conda activate myenv
python -m pytest backend/tests/unit/test_upload_cleanup.py backend/tests/unit/test_health.py -q
```

Run the generate/export integration tests:

```powershell
conda activate myenv
python -m pytest backend/tests/integration/test_generate_report.py -q
```

Manual check:

1. Start the backend.
2. Upload a workbook and note the created directory under `backend/tmp/uploads`.
3. Generate a report twice using the same `upload_id`; it should still work.
4. Set `UPLOAD_TTL_SECONDS` and `UPLOAD_CLEANUP_INTERVAL_SECONDS` to small
   values in `.env`.
5. Restart the backend and wait for the interval.
6. Confirm stale upload directories are deleted while fresh directories remain.

