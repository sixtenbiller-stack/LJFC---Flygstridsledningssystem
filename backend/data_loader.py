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
    try:
        raw = _load_json("geography.json")
    except (FileNotFoundError, KeyError):
        return Geography(
            meta={"name": "Default Geography"},
            features=[],
            terrain=[],
            defended_zones=[],
            map_background=None
        )
    return Geography(
        meta=raw["meta"],
        features=[GeoFeature(**f) for f in raw["features"]],
        terrain=[TerrainFeature(**t) for t in raw["terrain"]],
        defended_zones=[DefendedZone(**z) for z in raw["defended_zones"]],
        map_background=raw.get("map_background")
    )


def load_assets() -> list[Asset]:
    try:
        raw = _load_json("assets.json")
        return [Asset(**a) for a in raw["assets"]]
    except (FileNotFoundError, KeyError):
        return []


def load_scenario(scenario_id: str = "scenario-alpha") -> dict[str, Any]:
    filename = f"{scenario_id.replace('-', '_')}.json"
    try:
        return _load_json(filename)
    except FileNotFoundError:
        # Return empty scenario structure instead of crashing
        return {
            "meta": {"name": f"Empty ({scenario_id})", "duration_s": 240},
            "events": []
        }


def load_scenario_events(scenario_id: str = "scenario-alpha") -> list[ScenarioEvent]:
    data = load_scenario(scenario_id)
    return [ScenarioEvent(**e) for e in data.get("events", [])]


def load_scoring_params() -> dict[str, Any]:
    try:
        return _load_json("scoring_params.json")
    except FileNotFoundError:
        return {
            "scoring_weights": {
                "heading_toward_defended_zone": 0.4,
                "time_to_zone_inverse": 0.3,
                "speed_class_factor": 0.1,
                "confidence_level": 0.1,
                "target_value_proximity": 0.1,
                "raid_association_bonus": 0.0
            },
            "speed_class_map": {
                "slow": 0.1,
                "medium": 0.5,
                "fast": 1.0
            },
            "altitude_band_map": {
                "low": {"threat": 0.2},
                "medium": {"threat": 0.5},
                "high": {"threat": 0.8}
            },
            "threat_score_thresholds": {
                "critical": 0.8,
                "high": 0.6,
                "medium": 0.4,
                "low": 0.0
            }
        }


def load_mock_response(filename: str) -> dict[str, Any]:
    return {}


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
