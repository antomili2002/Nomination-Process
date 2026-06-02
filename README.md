# Scenario Delta Report Generator

## Overview
The **Scenario Delta Report Generator** is a reporting tool designed to parse, compare, and summarize scenario-based generation outputs from Excel workbooks. It handles complex nomination/scenario processes where scenarios form a logical chain (e.g., Base -> Intermediate -> Final).

## How It Works
1. **Upload**: Users upload an Excel Export containing an Info sheet and a Data sheet.
2. **Scenario Extraction**: The system identifies the scenarios from the Info sheet.
3. **Chain Configuration**: The user defines custom scenario comparison chains in the web UI.
4. **Machine Filtering**: Users can filter down to specific MACHINE_NAMEs, triggering instant front-end aggregations.
5. **Computation**: The backend processes step deltas and cumulative deltas across all months.
6. **Report Generation**: The frontend downloads a heavily formatted Excel representation mirroring Pivot Table aesthetics.

## Screenshots

### 1. Upload & Scenario Extraction
![Upload Step](docs/screenshots/upload.png)

### 2. Scenario Chain Configuration
![Chain Configuration](docs/screenshots/configure.png)

### 3. Machine Filter & Interactive Pivot
![Machine Filter UI](docs/screenshots/machine_filter.png)

---
*For detailed technical information, architecture, file structures, and implementation details, please see [project.md](project.md).*
