import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings


def job_output_dir(job_id: int, created_at: datetime | None = None) -> Path:
    settings = get_settings()
    day = (created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    path = settings.resolved_output_dir / day / f"job_{job_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_metadata(output_dir: Path, metadata: dict[str, Any]) -> Path:
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return metadata_path


def safe_relative_or_absolute(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.resolve())
