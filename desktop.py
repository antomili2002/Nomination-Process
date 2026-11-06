"""Desktop launcher for the Scenario Delta Report Generator.

Developed by Antonio Militello.
"""

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

APP_NAME = "Scenario Delta Report Generator"
AUTHOR = "Antonio Militello"


def _bundle_dir() -> Path:
    # PyInstaller extracts bundled files to sys._MEIPASS.
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _configure_environment() -> None:
    data_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ScenarioDeltaReport"
    os.environ.setdefault("UPLOAD_DIR", str(data_dir / "uploads"))
    os.environ.setdefault("REPORT_DIR", str(data_dir / "reports"))
    os.environ.setdefault("FRONTEND_DIST_DIR", str(_bundle_dir() / "frontend" / "dist"))


def _open_browser_when_ready(url: str) -> None:
    for _ in range(100):
        try:
            with urllib.request.urlopen(f"{url}/healthz", timeout=1):
                break
        except OSError:
            time.sleep(0.2)
    webbrowser.open(url)


def main() -> None:
    _configure_environment()

    import uvicorn

    from backend.main import app  # imported after env vars so settings pick them up
    from backend.storage.temp_files import purge_all_temp_data

    purge_all_temp_data()

    port = _free_port()
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print(f"  {APP_NAME}")
    print(f"  Developed by {AUTHOR}")
    print("=" * 60)
    print(f"  Running at {url}")
    print("  Close this window to stop the application.")
    print("=" * 60)

    threading.Thread(target=_open_browser_when_ready, args=(url,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
