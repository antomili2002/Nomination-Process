# Scenario Delta Report Generator

## 1. General Overview

The **Scenario Delta Report Generator** is a reporting tool for comparing scenario-based generation outputs from Excel workbooks.

The project reads an Excel export with:

- an **Info** sheet containing selected scenarios and their scenario IDs
- a **Data** sheet containing scenario results by output type, year, month, tariff, machine, and metric

The tool is designed for complex nomination or scenario processes where scenarios are not simply `base` and `new`, but instead form a chain:

```text
Base → Intermediate 1 → Intermediate 2 → ... → Final
```

Example:

```text
UK_BASE_EV → UK_OUTAGE_EV → UK_OFFICIAL_GIF
```

From this chain, the tool generates:

```text
Step deltas:
Intermediate 1 - Base
Intermediate 2 - Intermediate 1
Final - Intermediate N

Cumulative deltas:
Final - Base
```

This makes the reporting logic generalizable for **N intermediate scenarios**.

The final output is an Excel report containing monthly matrices, delta summaries, and optionally normalized source tables for native Excel PivotTables with interactive filters such as `MACHINE_NAME`.

---

## 2. Main Problem Solved

The original Excel workflow requires manual PivotTables and manual scenario comparison logic.

This project automates:

- scenario extraction from the Info sheet
- scenario-chain definition
- monthly aggregation
- step-delta calculation
- cumulative-delta calculation
- machine-level filtering
- static Excel report generation
- optional Excel template filling for native PivotTables and slicers

The project avoids hard-coded assumptions like:

```python
base_ev = "..."
new_ev = "..."
outage_ev = "..."
```

Instead, the user defines a scenario chain:

```python
ev_chain = [5, 1, 0]
```

Meaning:

```text
Base EV → Outage EV → Official EV
```

---

## 3. Input Definition

### 3.1 Input Excel Workbook

The input is an Excel workbook, for example:

```text
scenario_export.xlsx
```

Expected sheets:

```text
Info
Data
```

---

### 3.2 Info Sheet

The **Info** sheet contains the scenario metadata table.

The real header is not necessarily in the first row. The tool finds the row where the first column equals:

```text
Scenario Name
```

Expected scenario table columns:

```text
Scenario Name
Market Area
Cut Off Date
Scenario Type
Status
Run Date
Run End Date
Scenario ID
Main Query Execution Time (Sec)
```

The project extracts at least:

```text
SCENARIO_NAME
SCENARIO_ID
```

Example extracted table:

```text
Index | SCENARIO_NAME                              | SCENARIO_ID
0     | 20260513_UK_GIF_Official_EV               | 28064453
1     | 20260513_UK_GIF_Official_CNQ_Outages_EV   | 28064452
2     | 20260513_UK_GIF_Official_CNQ_Outages      | 28064451
3     | 20260513_UK_GIF_Official                  | 28064450
4     | UK_All_IV_M0_All_20260512_012200          | 28064432
5     | UK_All_EV_M0_All_20260512_001000          | 28064420
```

---

### 3.3 Data Sheet

The **Data** sheet contains the actual scenario results.

Important expected columns:

```text
SCENARIO_ID
SCENARIO_NAME
SCENARIO_TYPE
UNIT_COUNTRY
TPA
AS_OF_DATE
TIMESTEP
YEAR
MONTH
TARIFF
HOURS
PORTFOLIO
PLANT_NAME
UNIT_NAME
MACHINE_NAME
FUEL_NAME
RECORD_TYPE
POWER_PRICE__CUR_PER_MWH
POWER_POS__GWH
POWER_POS__MW
INTRINSIC_VALUE__CUR
EXTRINSIC_VALUE
OUTPUT_TYPE
SC_NAME
```

Minimum required columns for the core report:

```text
SCENARIO_NAME
SCENARIO_ID
OUTPUT_TYPE
YEAR
MONTH
TARIFF
MACHINE_NAME
POWER_POS__GWH
INTRINSIC_VALUE__CUR
EXTRINSIC_VALUE
```

---

### 3.4 Scenario Chain Input

The user defines scenario chains per output type.

Example:

```json
{
  "IV": [4, 2, 3],
  "EV": [5, 1, 0]
}
```

Meaning:

```text
IV: Base IV → Outage IV → Official IV
EV: Base EV → Outage EV → Official EV
```

The first index is always the base scenario.

The last index is the final scenario.

All indices between them are intermediate scenarios.

---

### 3.5 Machine Filter Input

The user can select all machines:

```json
{
  "selected_machines": null
}
```

or specific machines:

```json
{
  "selected_machines": ["T_CNQPS-1", "T_CNQPS-2"]
}
```

The machine filter must be applied before aggregation and before delta calculation.

---

## 4. Output Definition

The project can produce two types of Excel output:

1. Static formatted Excel report
2. Excel-template-based report with native PivotTables and slicers

---

### 4.1 Static Monthly Tables

The static monthly table looks like an Excel PivotTable.

Example:

```text
Sum of POWER_POS__GWH      Column Labels
Row Labels                 1      2      3   ...   12   Grand Total
Scenario A
    2026
        offpeak
        peak
    2027
        offpeak
        peak
Scenario B
    2026
        offpeak
        peak
Grand Total
```

Generated monthly tables:

```text
IV monthly POWER_POS__GWH
IV monthly INTRINSIC_VALUE__CUR
EV monthly EXTRINSIC_VALUE
```

These are static pandas-generated tables, not native Excel PivotTables.

---

### 4.2 Delta Summary Tables

The delta summary tables compare scenario pairs generated from the scenario chain.

For a chain:

```text
Base → Outage → Official
```

the generated comparisons are:

```text
Step deltas:
Outage - Base
Official - Outage

Cumulative deltas:
Outage - Base
Official - Base
```

Recommended delta output columns:

```text
OUTPUT_TYPE
DELTA_TYPE
COMPARISON_NAME
LEFT_SCENARIO
RIGHT_SCENARIO
MACHINE_NAME
YEAR
MONTH
TARIFF
METRIC
LEFT_VALUE
RIGHT_VALUE
DELTA_VALUE
```

---

### 4.3 Normalized Monthly Output

For native Excel PivotTables, the project should generate a normalized monthly source table.

Recommended columns:

```text
OUTPUT_TYPE
SCENARIO_STAGE
SCENARIO_NAME
MACHINE_NAME
YEAR
MONTH
TARIFF
METRIC
VALUE
```

Example:

```text
EV | 0 | UK_BASE_EV      | Machine A | 2026 | 5 | peak | EXTRINSIC_VALUE | 500
EV | 1 | UK_OUTAGE_EV    | Machine A | 2026 | 5 | peak | EXTRINSIC_VALUE | 700
EV | 2 | UK_OFFICIAL_GIF | Machine A | 2026 | 5 | peak | EXTRINSIC_VALUE | 1300
```

---

### 4.4 Normalized Delta Output

For native Excel PivotTables, the project should generate a normalized delta source table.

Recommended columns:

```text
OUTPUT_TYPE
DELTA_TYPE
COMPARISON_NAME
LEFT_SCENARIO
RIGHT_SCENARIO
MACHINE_NAME
YEAR
MONTH
TARIFF
METRIC
LEFT_VALUE
RIGHT_VALUE
DELTA_VALUE
```

Example:

```text
EV | step_delta       | Outage EV vs Base EV    | UK_OUTAGE_EV    | UK_BASE_EV | Machine A | 2026 | 5 | peak | EXTRINSIC_VALUE | 700  | 500 | 200
EV | cumulative_delta | Official EV vs Base EV  | UK_OFFICIAL_GIF | UK_BASE_EV | Machine A | 2026 | 5 | peak | EXTRINSIC_VALUE | 1300 | 500 | 800
```

---

## 5. Recommended Project Structure

```text
scenario-report-generator/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_upload.py
│   │   ├── routes_scenarios.py
│   │   ├── routes_reports.py
│   │   └── schemas.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   └── exceptions.py
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── scenario_chain.py
│   │   ├── delta_pair.py
│   │   └── report_config.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── workbook_service.py
│   │   ├── scenario_service.py
│   │   ├── report_service.py
│   │   └── validation_service.py
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── readers.py
│   │   ├── cleaning.py
│   │   ├── scenario_extraction.py
│   │   ├── chain_builder.py
│   │   ├── monthly_output.py
│   │   ├── delta_output.py
│   │   └── pivots.py
│   │
│   ├── excel/
│   │   ├── __init__.py
│   │   ├── static_writer.py
│   │   ├── template_writer.py
│   │   └── formatting.py
│   │
│   └── storage/
│       ├── __init__.py
│       ├── local_storage.py
│       └── temp_files.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       │
│       ├── api/
│       │   ├── client.ts
│       │   ├── upload.ts
│       │   ├── scenarios.ts
│       │   └── reports.ts
│       │
│       ├── components/
│       │   ├── FileUpload.tsx
│       │   ├── ScenarioTable.tsx
│       │   ├── ScenarioChainSelector.tsx
│       │   ├── MachineSelector.tsx
│       │   ├── ReportPreview.tsx
│       │   └── DownloadButton.tsx
│       │
│       ├── pages/
│       │   ├── UploadPage.tsx
│       │   ├── ConfigureReportPage.tsx
│       │   └── ResultPage.tsx
│       │
│       ├── types/
│       │   ├── scenario.ts
│       │   ├── report.ts
│       │   └── api.ts
│       │
│       └── utils/
│           └── formatting.ts
│
├── tests/
│   ├── unit/
│   │   ├── test_cleaning.py
│   │   ├── test_scenario_extraction.py
│   │   ├── test_chain_builder.py
│   │   ├── test_delta_pairs.py
│   │   ├── test_monthly_output.py
│   │   └── test_delta_output.py
│   │
│   ├── integration/
│   │   ├── test_full_report_generation.py
│   │   ├── test_excel_template_filling.py
│   │   └── test_api_upload_to_download.py
│   │
│   └── fixtures/
│       ├── sample_input.xlsx
│       ├── expected_scenarios.csv
│       ├── expected_monthly_output.csv
│       └── expected_delta_output.csv
│
├── templates/
│   └── report_template.xlsx
│
├── examples/
│   ├── sample_config.json
│   └── sample_run.py
│
└── scripts/
    ├── run_backend.sh
    ├── run_frontend.sh
    └── generate_sample_report.py
```

---

## 6. Backend File Responsibilities

### `backend/main.py`

Creates the FastAPI app.

Responsibilities:

```text
- initialize FastAPI
- register routers
- configure CORS
- configure exception handling
```

---

### `backend/api/routes_upload.py`

Handles Excel upload.

Endpoint:

```text
POST /upload
```

Responsibilities:

```text
- receive uploaded Excel file
- save temporary file
- read Info and Data sheets
- extract scenario info
- extract available MACHINE_NAME values
- return upload ID and extracted metadata
```

---

### `backend/api/routes_scenarios.py`

Handles scenario-chain validation.

Endpoint:

```text
POST /scenarios/validate-chain
```

Responsibilities:

```text
- validate selected scenario indices
- validate IV and EV chains
- ensure each chain has at least two scenarios
- resolve chain indices to scenario names
- return generated comparison pairs
```

---

### `backend/api/routes_reports.py`

Handles report generation and download.

Endpoints:

```text
POST /reports/generate
GET /reports/{report_id}/download
```

Responsibilities:

```text
- receive report configuration
- generate monthly output
- generate delta output
- create Excel report
- return download URL
```

---

### `backend/api/schemas.py`

Contains Pydantic models.

Recommended schemas:

```text
ScenarioInfoRow
UploadResponse
ScenarioChainRequest
ReportGenerationRequest
ReportGenerationResponse
MachineSelection
MetricSelection
```

---

### `backend/core/config.py`

Loads environment variables.

Responsibilities:

```text
- read .env values
- define upload directory
- define report directory
- define CORS origins
- define max upload size
```

---

### `backend/processing/readers.py`

Reads Excel input files.

Responsibilities:

```text
- read workbook
- read Info sheet with header=None
- read Data sheet
- check required sheets
```

---

### `backend/processing/cleaning.py`

Cleans raw data.

Responsibilities:

```text
- strip column names
- convert decimal-comma numbers
- convert YEAR and MONTH to numeric values
- clean SCENARIO_NAME
- clean OUTPUT_TYPE
- clean TARIFF
- clean MACHINE_NAME
```

---

### `backend/processing/scenario_extraction.py`

Extracts scenarios from the Info sheet.

Responsibilities:

```text
- find header row containing "Scenario Name"
- extract scenario rows below the header
- remove empty rows
- return SCENARIO_NAME and SCENARIO_ID
```

---

### `backend/processing/chain_builder.py`

Builds scenario chains and delta pairs.

Responsibilities:

```text
- resolve scenario indices to names
- create step-delta pairs
- create cumulative-delta pairs
- optionally remove duplicate pairs
```

---

### `backend/processing/monthly_output.py`

Creates monthly outputs.

Responsibilities:

```text
- aggregate metric values by scenario, machine, year, month, tariff
- support selected machines
- return normalized monthly output
- optionally create static monthly matrix tables
```

---

### `backend/processing/delta_output.py`

Creates delta outputs.

Responsibilities:

```text
- calculate left scenario values
- calculate right scenario values
- calculate delta values
- support step and cumulative deltas
- support selected machines
```

---

### `backend/excel/static_writer.py`

Writes static Excel reports.

Responsibilities:

```text
- write monthly matrix tables
- write delta summary tables
- apply Excel formatting
- set column widths
- format numbers without scientific notation
```

---

### `backend/excel/template_writer.py`

Fills an Excel template.

Responsibilities:

```text
- write Monthly_Output table
- write Delta_Output table
- preserve workbook structure
- support native PivotTables and slicers if template already contains them
```

---

## 7. Frontend Structure

The frontend should guide the user through a simple workflow:

```text
Upload Excel → Select scenario chains → Select machines → Generate report → Download Excel
```

---

### `frontend/src/api/client.ts`

Creates the API client.

Responsibilities:

```text
- configure backend base URL
- attach common headers
- handle API errors
```

---

### `frontend/src/api/upload.ts`

Handles upload requests.

Responsibilities:

```text
- send Excel file to backend
- receive scenario info and machine list
```

---

### `frontend/src/api/scenarios.ts`

Handles scenario-chain validation.

Responsibilities:

```text
- send selected IV and EV chains
- receive generated delta pairs
```

---

### `frontend/src/api/reports.ts`

Handles report generation.

Responsibilities:

```text
- send final report configuration
- receive report download URL
```

---

### `frontend/src/components/FileUpload.tsx`

Responsibilities:

```text
- select Excel file
- upload file
- show upload status
```

---

### `frontend/src/components/ScenarioTable.tsx`

Responsibilities:

```text
- display extracted scenario table
- show scenario index
- show SCENARIO_NAME
- show SCENARIO_ID
```

---

### `frontend/src/components/ScenarioChainSelector.tsx`

Responsibilities:

```text
- allow user to define scenario chain
- support drag-and-drop ordering or ordered dropdowns
- define Base → Intermediate(s) → Final
```

---

### `frontend/src/components/MachineSelector.tsx`

Responsibilities:

```text
- show all available MACHINE_NAME values
- allow selecting all machines
- allow selecting specific machines
```

---

### `frontend/src/components/ReportPreview.tsx`

Responsibilities:

```text
- preview selected scenario chains
- preview generated delta pairs
- preview selected machines
```

---

### `frontend/src/components/DownloadButton.tsx`

Responsibilities:

```text
- generate report
- download Excel output
```

---

## 8. Test Structure

### 8.1 Unit Tests

Unit tests verify individual functions.

Recommended files:

```text
tests/unit/test_cleaning.py
tests/unit/test_scenario_extraction.py
tests/unit/test_chain_builder.py
tests/unit/test_delta_pairs.py
tests/unit/test_monthly_output.py
tests/unit/test_delta_output.py
```

---

### 8.2 Integration Tests

Integration tests verify full workflows.

Recommended files:

```text
tests/integration/test_full_report_generation.py
tests/integration/test_excel_template_filling.py
tests/integration/test_api_upload_to_download.py
```

---

### 8.3 Test Fixtures

Store deterministic test input files in:

```text
tests/fixtures/
```

Recommended fixtures:

```text
sample_input.xlsx
expected_scenarios.csv
expected_monthly_output.csv
expected_delta_output.csv
```

The test workbook should contain simple known values:

```text
Base = 500
Outage = 700
Official = 1300
```

Expected deltas:

```text
Outage - Base = 200
Official - Outage = 600
Official - Base = 800
```

---

## 9. Coding Best Practices

### 9.1 Keep Business Logic Out of API Routes

Bad:

```python
@app.post("/reports/generate")
def generate_report():
    # large pandas logic here
```

Good:

```python
@app.post("/reports/generate")
def generate_report(request: ReportGenerationRequest):
    return report_service.generate_report(request)
```

API routes should only handle HTTP input/output.

---

### 9.2 Use Small Functions

Good function examples:

```text
read_workbook()
extract_scenarios_from_info()
clean_decimal_comma_columns()
build_delta_pairs()
create_monthly_output()
create_delta_output()
write_static_excel_report()
```

Each function should do one job.

---

### 9.3 Use Long Format Internally

Good internal format:

```text
SCENARIO_NAME | MACHINE_NAME | YEAR | MONTH | TARIFF | METRIC | VALUE
```

Avoid using this internally:

```text
Scenario | Jan | Feb | Mar | ...
```

Wide tables are fine only for final Excel display.

---

### 9.4 Do Not Hard-Code Scenario Names

Bad:

```python
base_ev = "UK_All_EV_M0_All_20260512_001000"
```

Good:

```python
scenario_chains = {
    "EV": [5, 1, 0]
}
```

---

### 9.5 Validate User Input Early

Validate:

```text
- uploaded file type
- required sheets exist
- required columns exist
- scenario chain indices exist
- each chain has at least two scenarios
- selected machines exist in the data
```

---

### 9.6 Keep Raw Data Immutable

Avoid modifying raw input data directly.

Use:

```python
data = df.copy()
```

inside processing functions.

---

### 9.7 Handle Decimal Comma Correctly

Excel exports may store numbers like:

```text
50,4566
```

They must become:

```text
50.4566
```

Use a dedicated cleaning function before aggregation.

---

### 9.8 Avoid Scientific Notation in Outputs

Large values such as:

```text
2.135738e+07
```

should be shown as:

```text
21357380
```

Use integer rounding and Excel number formats like:

```text
0
```

or:

```text
#,##0
```

depending on reporting requirements.

---

### 9.9 Use Type Hints

Example:

```python
def build_delta_pairs(
    scenario_info: pd.DataFrame,
    chain_indices: list[int],
) -> pd.DataFrame:
    ...
```

---

### 9.10 Raise Clear Errors

Bad:

```python
except Exception:
    pass
```

Good:

```python
raise ValueError("Column POWER_POS__GWH is missing from the Data sheet.")
```

---

### 9.11 Add Logging

Log important steps:

```text
- file uploaded
- scenarios extracted
- scenario chains selected
- machines selected
- report generated
- output path
```

---

## 10. Environment Variables

Create a `.env` file in the project root.

Example `.env`:

```env
APP_NAME=Scenario Delta Report Generator
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

UPLOAD_DIR=storage/uploads
REPORT_DIR=storage/reports
TEMPLATE_PATH=templates/report_template.xlsx

MAX_UPLOAD_SIZE_MB=100

LOG_LEVEL=INFO
```

Create a `.env.example` file with the same keys but no sensitive values.

Do not commit the real `.env` file.

---

## 11. Backend Requirements

Create `requirements.txt`:

```txt
fastapi
uvicorn[standard]
python-multipart
pydantic
pydantic-settings
python-dotenv

pandas
numpy
openpyxl
xlsxwriter

pytest
pytest-cov
httpx

loguru
```

Optional packages for native local Excel automation on Windows:

```txt
xlwings
pywin32
```

Use `xlwings` or `pywin32` only if the application needs to create or refresh native Excel PivotTables through installed Excel.

For server-side generation, prefer:

```text
pandas
openpyxl
xlsxwriter
```

---

## 12. Frontend Requirements

Recommended frontend stack:

```text
React
TypeScript
Vite
Axios
TanStack Query
```

Create frontend:

```bash
npm create vite@latest frontend -- --template react-ts
```

Install packages:

```bash
npm install axios @tanstack/react-query
```

Optional UI packages:

```bash
npm install lucide-react
npm install @radix-ui/react-select @radix-ui/react-checkbox
npm install clsx tailwind-merge
```

---

## 13. Local Development Setup

### 13.1 Backend Setup

Create environment:

```bash
python -m venv .venv
```

Activate environment.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

Install backend packages:

```bash
pip install -r requirements.txt
```

Run backend:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

---

### 13.2 Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

```text
Frontend: http://localhost:5173
Backend:  http://127.0.0.1:8000
```

---

## 14. Example Workflow

1. User uploads Excel workbook.
2. Backend extracts scenario info.
3. Frontend displays scenarios with indices.
4. User defines chains:

```json
{
  "IV": [4, 2, 3],
  "EV": [5, 1, 0]
}
```

5. User selects all machines or specific `MACHINE_NAME` values.
6. Backend builds step and cumulative delta pairs.
7. Backend creates monthly output.
8. Backend creates delta output.
9. Backend writes Excel report.
10. User downloads the Excel report.

---

## 15. Future Improvements

Potential next steps:

```text
- native Excel template with PivotTables and slicers
- automatic scenario-chain suggestion based on names
- drag-and-drop scenario-chain UI
- frontend report preview
- background jobs for large files
- authentication for internal users
- audit logs for generated reports
- Power BI export
- config-based metric definitions
```

---

## 16. Recommended First Implementation

Start with:

```text
FastAPI backend
React frontend
static Excel report generation
scenario-chain selection
machine filter before aggregation
unit tests for delta logic
```

Then add native Excel PivotTable template support only after the static report logic is correct.

The most important project abstraction is:

```text
Scenario chains → Delta pairs → Long output tables → Excel report
```


## 17. Completed Features & Implementation Details

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
