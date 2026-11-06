# PyInstaller spec - build with: pyinstaller packaging/ScenarioDeltaReport.spec
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
    a.binaries,
    a.datas,
    [],
    name="ScenarioDeltaReport",
    console=True,
    upx=False,
    version=SPECPATH + "/version_info.txt",
)
