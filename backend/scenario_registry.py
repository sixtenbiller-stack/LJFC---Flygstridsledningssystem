"""Scenario discovery and metadata for NEON COMMAND."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "neon-command-data"
GENERATED_DIR = DATA_DIR / "generated"
RUNTIME_DIR = DATA_DIR / "runtime"
CUSTOM_DIR = DATA_DIR / "custom"


SCENARIO_LABELS: dict[str, dict[str, Any]] = {}


def _read_meta(path: Path) -> dict[str, Any]:
    try:
        with open(path) as f:
            data = json.load(f)
        meta = data.get("meta", {})
        events = data.get("events", [])
        track_count = sum(1 for e in events if e.get("event_type") == "TRACK_CREATED")
        group_count = sum(1 for e in events if e.get("event_type") == "GROUP_FORMED")
        extended = meta.get("group_aware", False) or bool(meta.get("extended_fields"))
        return {
            "scenario_id": meta.get("scenario_id", path.stem),
            "file_id": path.stem,
            "source_file": str(path),
            "duration_s": meta.get("duration_s"),
            "seed": meta.get("seed"),
            "template": meta.get("template"),
            "track_count": track_count,
            "group_count": group_count,
            "extended_fields": extended,
            "total_events": meta.get("total_events", len(events)),
        }
    except Exception:
        return {"scenario_id": path.stem, "file_id": path.stem, "source_file": str(path)}


def discover() -> list[dict[str, Any]]:
    """Return metadata for all discoverable scenarios."""
    results: list[dict[str, Any]] = []

    for scan_dir, source_type in [(DATA_DIR, "base"), (GENERATED_DIR, "generated"), (CUSTOM_DIR, "custom")]:
        if not scan_dir.exists():
            continue
        for p in sorted(scan_dir.glob("scenario_*.json")):
            entry = _read_meta(p)
            label = SCENARIO_LABELS.get(p.stem, {})
            entry.update({
                "source_type": source_type,
                "title": label.get("title", entry.get("scenario_id", p.stem)),
                "short_description": label.get("short", ""),
                "recommended_mode": label.get("recommended_mode", "replay"),
                "jury_demo": label.get("jury_demo", False),
            })
            results.append(entry)

    return results


def load_scenario_raw(file_id: str) -> dict[str, Any]:
    """Load a scenario JSON by file_id, checking base then generated dirs."""
    for d in [DATA_DIR, GENERATED_DIR, CUSTOM_DIR]:
        path = d / f"{file_id}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
    raise FileNotFoundError(f"Scenario not found: {file_id}")


def runtime_copy_path(file_id: str, session_tag: str = "") -> Path:
    """Path for a runtime mutable session copy."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"_{session_tag}" if session_tag else ""
    return RUNTIME_DIR / f"{file_id}{suffix}_live.json"
