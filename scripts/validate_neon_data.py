#!/usr/bin/env python3
"""Validate the active minimal NEON COMMAND data path."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
VENV_PYTHON = BACKEND / "venv" / "bin" / "python"
if not os.environ.get("NEON_VALIDATOR_REEXEC") and VENV_PYTHON.exists() and Path(sys.executable) != VENV_PYTHON:
    os.environ["NEON_VALIDATOR_REEXEC"] = "1"
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

sys.path.insert(0, str(BACKEND))

from data_validation import (  # noqa: E402
    NeonDataValidationError,
    validate_assets_data,
    validate_ato_data,
    validate_geography_data,
    validate_scenario_data,
    validate_scoring_params_data,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _check(label: str, path: Path, validator) -> list[str]:
    try:
        validator(_load(path), str(path))
        print(f"OK   {label}: {path.relative_to(ROOT)}")
        return []
    except Exception as exc:
        print(f"FAIL {label}: {path.relative_to(ROOT)}")
        if isinstance(exc, NeonDataValidationError):
            for issue in exc.issues:
                print(f"  - {issue.path}: {issue.message}")
        else:
            print(f"  - $: {exc}")
        return [str(exc)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extended", action="store_true")
    args = parser.parse_args()
    data_dir = ROOT / "neon-command-data"
    errors: list[str] = []
    errors += _check("geography", data_dir / "geography.json", validate_geography_data)
    errors += _check("assets", data_dir / "assets.json", validate_assets_data)
    errors += _check("scoring", data_dir / "scoring_params.json", validate_scoring_params_data)
    if (data_dir / "ato_minimal_alpha.json").exists():
        errors += _check("ato", data_dir / "ato_minimal_alpha.json", validate_ato_data)
    scenario_paths = [data_dir / "scenario_minimal_alpha.json"]
    if args.extended:
        scenario_paths = sorted(data_dir.glob("scenario_*.json"))
        for subdir in ["generated", "runtime"]:
            folder = data_dir / subdir
            if folder.exists():
                scenario_paths.extend(sorted(folder.glob("scenario_*.json")))
    for path in scenario_paths:
        errors += _check("scenario", path, validate_scenario_data)
    if errors:
        print(f"\nNEON data validation failed: {len(errors)} file(s) with errors.")
        return 1
    print(f"\nNEON data validation passed: {4 + len(scenario_paths)} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
