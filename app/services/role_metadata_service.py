from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from flask import current_app


def _metadata_path() -> Path:
    base = Path(current_app.root_path)
    config_dir = base / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "role_metadata.json"


def load_role_metadata() -> Dict[str, Dict[str, Any]]:
    path = _metadata_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except Exception:
        current_app.logger.warning("Failed to read role metadata file; using empty defaults", exc_info=True)
    return {}


def save_role_metadata(metadata: Dict[str, Dict[str, Any]]) -> None:
    path = _metadata_path()
    with path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, sort_keys=True)
