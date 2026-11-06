# PyInstaller spec - build with: pyinstaller packaging/ScenarioDeltaReport.spec
# Onedir mode: no unpacking to %TEMP% on every start, so startup is much faster.
from PyInstaller.utils.hooks import collect_submodules

ROOT = SPECPATH + "/.."

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("backend")
    + ["python_calamine", "xlsxwriter", "openpyxl", "multipart"]
)

a = Analysis(
    [ROOT + "/desktop.py"],
    pathex=[ROOT],
    datas=[(ROOT + "/frontend/dist", "frontend/dist")],
    hiddenimports=hiddenimports,
    excludes=["pytest", "backend.tests", "tkinter", "matplotlib", "IPython"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScenarioDeltaReport",
    console=True,
    upx=False,
    icon=SPECPATH + "/app.ico",
    version=SPECPATH + "/version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="ScenarioDeltaReport",
)
