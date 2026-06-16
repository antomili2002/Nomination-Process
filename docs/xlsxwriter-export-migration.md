# Excel Export XlsxWriter Migration

This document explains the Excel export changes in `backend/excel/report_writer.py`.
The goal was to speed up `.xlsx` generation while preserving the existing export
contract.

## What Changed

The report writer now uses `XlsxWriter` instead of `openpyxl` to generate the
downloadable workbook.

The public Python interface is unchanged:

```python
write_report(report_data: dict, info_df: pd.DataFrame, data_df: pd.DataFrame) -> bytes
```

The HTTP export endpoint is also unchanged:

```text
POST /reports/export
```

The export still includes:

- all generated report sheets
- `Info`
- `Data`

We intentionally did not remove the `Data` sheet. The optimization keeps the
current workbook contents and improves how the workbook is written.

## Why This Is Faster

The previous `openpyxl` writer used this pattern for most cells:

```python
c = ws.cell(row=row, column=col, value=value)
c.font = font
c.fill = fill
c.alignment = Alignment(indent=indent)
c.number_format = num_fmt
c.border = border
```

That is expensive because each cell is created and styled individually. It was
especially costly for the raw `Data` sheet, where every dataframe value went
through `_w(...)` and `_safe(...)`.

The new writer improves this in four ways:

1. It creates reusable XlsxWriter formats once.
2. It writes raw dataframe sheets row-by-row with `write_row(...)`.
3. It converts missing dataframe values once at dataframe level.
4. It writes through a temporary file with `constant_memory=True`.

The current pipeline is now:

```text
processed upload artifacts
        |
        v
report_service aggregation cache
        |
        v
report_data dict
        |
        v
XlsxWriter report writer
        |
        v
.xlsx bytes
```

## Constant Memory Mode

`write_report(...)` creates the workbook like this:

```python
wb = xlsxwriter.Workbook(tmp_path, {"constant_memory": True})
```

This lets XlsxWriter flush rows as it writes them instead of keeping the full
workbook structure in memory. It is a better fit for large generated reports
than building everything with random-access cell objects.

Because constant-memory mode is row-oriented, the implementation writes sheets
in forward order and avoids revisiting previous rows.

## Raw Info And Data Sheets

The raw `Info` and `Data` sheets are still exported.

The important performance change is that they are written row-wise:

```python
clean_df = df.astype(object).where(pd.notna(df), None)

if write_header:
    ws.write_row(row_idx, 0, [str(col) for col in clean_df.columns], formats["default"])

for row in clean_df.itertuples(index=False, name=None):
    ws.write_row(row_idx, 0, row, formats["default"])
```

This avoids:

- per-cell `openpyxl` object creation
- per-cell style assignment
- per-cell `pd.isna(...)`

The `Data` sheet remains in the workbook for compatibility and auditability.

## Formatting Compatibility

The writer still preserves the formatting covered by tests:

- sheet names
- sheet ordering
- `Aptos Narrow`, 11pt font
- bold report headers and totals
- blue fill color `#C0E6F5`
- number format `#,##0`
- gridlines hidden on generated sheets
- key top and bottom borders
- report, `Info`, and `Data` values

The generated `.xlsx` bytes are not expected to be byte-for-byte identical to
the previous openpyxl output. The workbook behavior and visible layout are the
compatibility target.

## Files Changed

Main implementation:

```text
backend/excel/report_writer.py
```

Regression tests:

```text
backend/tests/unit/test_report_writer.py
```

The regression tests now also verify that XlsxWriter is used with
`constant_memory=True`.

## How To Check The Changes

Run all commands from the repository root.

### 1. Activate the environment

```powershell
conda activate myenv
```

### 2. Run the report writer tests

```powershell
python -m pytest backend/tests/unit/test_report_writer.py -q
```

Expected result:

```text
34 passed
```

### 3. Run the export integration tests

```powershell
python -m pytest backend/tests/integration/test_generate_report.py::TestExportReport -q
```

Expected result:

```text
6 passed
```

### 4. Run the full backend suite

```powershell
python -m pytest backend/tests -q
```

Expected result from the implementation run:

```text
147 passed
```

The current environment may still print warnings about Starlette/httpx and
pytest cache permissions. Those warnings are unrelated to the XlsxWriter
migration.

### 5. Manual API Check

Start the backend:

```powershell
python -m uvicorn backend.main:app --reload
```

Then:

1. Upload a workbook with `POST /upload`.
2. Generate or preview the report as usual.
3. Download with `POST /reports/export`.
4. Open the `.xlsx` file.

Verify that the workbook still contains the generated report sheets plus:

```text
Info
Data
```

## Expected Performance Impact

This change targets the final Excel writing stage.

It should help most when:

- the raw `Data` sheet is large
- many report sheets are generated
- styling overhead dominates export time
- memory pressure is high during `.xlsx` creation

This change works together with the previous backend caching work:

- processed upload artifacts avoid reparsing and recleaning Excel
- report aggregation cache avoids repeated pandas groupby work
- XlsxWriter reduces final workbook writing overhead

If export is still too slow after this migration, the next performance decision
would be a product-level tradeoff: whether the raw `Data` sheet should become
optional. That was not part of this implementation, because the current
intended behavior is to keep exporting `Data`.
