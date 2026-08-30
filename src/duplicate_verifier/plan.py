from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from duplicate_verifier.models import AnalysisResult, ImageFile


PLAN_VERSION = 1


def default_plan_path() -> Path:
    override = os.environ.get("DUPCHECK_PLAN")
    if override:
        return Path(override)
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "duplicate-verifier" / "last-plan.json"


def save_plan(
    root: Path,
    result: AnalysisResult,
    *,
    path: Path | None = None,
) -> Path:
    destination = path or default_plan_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": PLAN_VERSION,
        "root": str(root.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {
                "path": str(item.path.resolve()),
                "size_bytes": item.size_bytes,
                "keep": str(group.keep.path.resolve()),
            }
            for group in result.groups
            for item in group.delete
        ],
    }
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def load_plan(path: Path | None = None) -> dict[str, Any] | None:
    source = path or default_plan_path()
    if not source.is_file():
        return None
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("version") != PLAN_VERSION:
        return None
    if not isinstance(data.get("files"), list):
        return None
    return data


def clear_plan(path: Path | None = None) -> None:
    source = path or default_plan_path()
    try:
        source.unlink(missing_ok=True)
    except OSError:
        pass


def planned_files(plan: dict[str, Any]) -> list[ImageFile]:
    files: list[ImageFile] = []
    for entry in plan.get("files", []):
        if not isinstance(entry, dict):
            continue
        raw_path = entry.get("path")
        if not raw_path:
            continue
        files.append(
            ImageFile(
                path=Path(str(raw_path)),
                size_bytes=int(entry.get("size_bytes") or 0),
            )
        )
    return files
