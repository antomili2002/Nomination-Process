# Builds dist\ScenarioDeltaReport\ (app folder) and, if Inno Setup is installed, the setup installer.
# Run from the repo root with the conda env active.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    Push-Location frontend
    npm install
    npm run build
    Pop-Location

    python -m pip install pyinstaller pillow

    # Convert the app logo to a multi-size Windows icon.
    python -c "from PIL import Image; Image.open('frontend/public/Uniper Energie-Analytics App-Symbol.png').convert('RGBA').save('packaging/app.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"

    python -m PyInstaller --noconfirm --clean packaging/ScenarioDeltaReport.spec
    Write-Host "Built: $root\dist\ScenarioDeltaReport\ScenarioDeltaReport.exe"

    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($iscc) {
        & $iscc packaging\installer.iss
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }
        Write-Host "Installer: $root\dist\ScenarioDeltaReport-Setup-0.1.0.exe"
    }
    else {
        Write-Host "Inno Setup 6 not found - skipped installer. Zip dist\ScenarioDeltaReport to distribute instead."
    }
}
finally {
    Pop-Location
}
