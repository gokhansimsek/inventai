"""The run manifest: what a run used and produced, so it can be reproduced."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from retail_analytics.config import Settings
from retail_analytics.io.readers import TABLE_FILES
from retail_analytics.validation.engine import RowCounts


def write_manifest(
    settings: Settings, row_counts: dict[str, RowCounts], started_at: datetime
) -> Path:
    """Write ``run_manifest.json`` into the run's output folder.

    Args:
        settings (Settings): The settings the run used.
        row_counts (dict[str, RowCounts]): Raw, clean and rejected rows per table.
        started_at (datetime): When the run started.

    Returns:
        Path: The manifest file written.
    """
    manifest = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "settings": settings.model_dump(mode="json"),
        "input_files": {
            filename: _describe(settings.data_dir / filename) for filename in TABLE_FILES.values()
        },
        "row_counts": {table: asdict(counts) for table, counts in row_counts.items()},
    }
    path = settings.output_dir / "run_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _describe(path: Path) -> dict[str, str | int]:
    """Identify an input file by size and content hash.

    Args:
        path (Path): The input file.

    Returns:
        dict[str, str | int]: ``bytes`` (file size) and ``sha256`` (hex digest).
    """
    content = path.read_bytes()
    return {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
