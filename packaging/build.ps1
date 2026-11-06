# Builds dist\ScenarioDeltaReport.exe. Run from the repo root with the conda env active.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    Push-Location frontend
    npm install
    npm run build
    Pop-Location

    python -m pip install pyinstaller
    python -m PyInstaller --noconfirm --clean packaging/ScenarioDeltaReport.spec
    Write-Host "Built: $root\dist\ScenarioDeltaReport.exe"
}
finally {
    Pop-Location
}
