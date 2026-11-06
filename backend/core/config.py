from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upload_dir: Path = Path("backend/tmp/uploads")
    report_dir: Path = Path("backend/tmp/reports")
    cors_origins: list[str] = ["http://localhost:5173"]
    max_upload_bytes: int = 150 * 1024 * 1024  # 150 MB
    upload_ttl_seconds: int = 4 * 3600
    upload_cleanup_interval_seconds: int = 15 * 60
    # Built frontend (frontend/dist); when set, the API also serves the UI.
    frontend_dist_dir: Path | None = None

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
