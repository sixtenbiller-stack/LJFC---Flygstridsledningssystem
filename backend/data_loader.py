"""Load all JSON data files from the neon-command-data directory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models import Geography, Asset, ScenarioEvent, GeoFeature, TerrainFeature, DefendedZone

DATA_DIR = Path(__file__).resolve().parent.parent / "neon-command-data"


def _load_json(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    with open(path) as f:
        return json.load(f)


def load_geography() -> Geography:
    raw = _load_json("geography.json")
    return Geography(
        meta=raw["meta"],
        features=[GeoFeature(**f) for f in raw["features"]],
        terrain=[TerrainFeature(**t) for t in raw["terrain"]],
        defended_zones=[DefendedZone(**z) for z in raw["defended_zones"]],
        map_background=raw.get("map_background")
    )


def load_assets() -> list[Asset]:
    raw = _load_json("assets.json")
    return [Asset(**a) for a in raw["assets"]]


def load_scenario(scenario_id: str = "scenario-alpha") -> dict[str, Any]:
    filename = f"{scenario_id.replace('-', '_')}.json"
    return _load_json(filename)


def load_scenario_events(scenario_id: str = "scenario-alpha") -> list[ScenarioEvent]:
    data = load_scenario(scenario_id)
    return [ScenarioEvent(**e) for e in data["events"]]


def load_scoring_params() -> dict[str, Any]:
    return _load_json("scoring_params.json")


def load_mock_response(filename: str) -> dict[str, Any]:
    path = DATA_DIR / "mock_responses" / filename
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_planning_guardrails() -> dict[str, Any]:
    try:
        return _load_json("planning_guardrails.json")
    except FileNotFoundError:
        return {
            "default_max_commit_pct": 75,
            "reserve_policy_default": "preserve_qra_reserve",
            "preserve_qra_default": True,
            "allow_existential_override": True,
            "explanation_style": "direct_factual",
        }
