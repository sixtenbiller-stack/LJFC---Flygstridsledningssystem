"""Validation helpers for NEON COMMAND synthetic JSON data."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from models import Alert, Asset, DefendedZone, GeoFeature, Geography, TerrainFeature, Track


@dataclass
class ValidationIssue:
    path: str
    message: str


class NeonDataValidationError(ValueError):
    def __init__(self, source: str, issues: list[ValidationIssue]) -> None:
        self.source = source
        self.issues = issues
        joined = "; ".join(f"{i.path}: {i.message}" for i in issues[:8])
        super().__init__(f"Invalid NEON data in {source}: {joined}")


def _pydantic_issues(prefix: str, exc: ValidationError) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            path=f"{prefix}.{'.'.join(str(part) for part in err.get('loc', ())) }".rstrip("."),
            message=err.get("msg", "invalid value"),
        )
        for err in exc.errors()
    ]


def validate_geography_data(raw: dict[str, Any], source: str = "geography.json") -> None:
    issues: list[ValidationIssue] = []
    if raw.get("schema_version") != "neon.geography.v1":
        issues.append(ValidationIssue("$.schema_version", "must be neon.geography.v1"))
    try:
        Geography(
            meta=raw["meta"],
            features=[GeoFeature(**f) for f in raw["features"]],
            terrain=[TerrainFeature(**t) for t in raw["terrain"]],
            defended_zones=[DefendedZone(**z) for z in raw["defended_zones"]],
        )
    except KeyError as exc:
        issues.append(ValidationIssue(f"$.{exc.args[0]}", "missing required key"))
    except ValidationError as exc:
        issues.extend(_pydantic_issues("$", exc))
    if issues:
        raise NeonDataValidationError(source, issues)


def validate_assets_data(raw: dict[str, Any], source: str = "assets.json") -> None:
    issues: list[ValidationIssue] = []
    if raw.get("schema_version") != "neon.assets.v1":
        issues.append(ValidationIssue("$.schema_version", "must be neon.assets.v1"))
    for idx, asset in enumerate(raw.get("assets", [])):
        try:
            Asset(**asset)
        except ValidationError as exc:
            issues.extend(_pydantic_issues(f"$.assets[{idx}]", exc))
    if "assets" not in raw:
        issues.append(ValidationIssue("$.assets", "missing required assets array"))
    if issues:
        raise NeonDataValidationError(source, issues)


def validate_scoring_params_data(raw: dict[str, Any], source: str = "scoring_params.json") -> None:
    issues: list[ValidationIssue] = []
    if raw.get("schema_version") != "neon.scoring.v1":
        issues.append(ValidationIssue("$.schema_version", "must be neon.scoring.v1"))
    for key in ["scoring_weights", "speed_class_map", "altitude_band_map", "threat_score_thresholds"]:
        if key not in raw:
            issues.append(ValidationIssue(f"$.{key}", "missing required key"))
        elif not isinstance(raw[key], dict):
            issues.append(ValidationIssue(f"$.{key}", "expected object"))
    for key in ["confidence_threshold_for_alert", "confidence_threshold_for_high_priority"]:
        if key not in raw:
            issues.append(ValidationIssue(f"$.{key}", "missing required key"))
    if issues:
        raise NeonDataValidationError(source, issues)


def validate_ato_data(raw: dict[str, Any], source: str = "ato.json") -> None:
    issues: list[ValidationIssue] = []
    if raw.get("schema_version") != "neon.ato.v1":
        issues.append(ValidationIssue("$.schema_version", "must be neon.ato.v1"))
    for key in [
        "ato_id",
        "name",
        "description",
        "valid_from_s",
        "valid_to_s",
        "planning_intent",
        "missions",
        "authority",
        "notes",
    ]:
        if key not in raw:
            issues.append(ValidationIssue(f"$.{key}", "missing required key"))
    if issues:
        raise NeonDataValidationError(source, issues)


def validate_scenario_data(raw: dict[str, Any], source: str = "scenario") -> None:
    issues: list[ValidationIssue] = []
    allowed_top = {"schema_version", "schema_profile", "meta", "initial_state", "events"}
    for key in raw:
        if key not in allowed_top:
            issues.append(ValidationIssue(f"$.{key}", "unknown top-level key"))
    if raw.get("schema_version") != "neon.scenario.v1":
        issues.append(ValidationIssue("$.schema_version", "must be neon.scenario.v1"))
    if raw.get("schema_profile") not in {"minimal", None}:
        issues.append(ValidationIssue("$.schema_profile", "only minimal profile is active by default"))
    meta = raw.get("meta", {})
    for key in ["scenario_id", "name", "duration_s"]:
        if key not in meta:
            issues.append(ValidationIssue(f"$.meta.{key}", "missing required key"))
    previous_t = -1.0
    for idx, event in enumerate(raw.get("events", [])):
        path = f"$.events[{idx}]"
        if not {"t_s", "event_type", "data"}.issubset(event):
            issues.append(ValidationIssue(path, "event must include t_s, event_type, data"))
            continue
        if event["t_s"] < previous_t:
            issues.append(ValidationIssue(f"{path}.t_s", "events must be sorted by time"))
        previous_t = event["t_s"]
        if event["event_type"] == "TRACK_CREATED":
            try:
                Track(**event["data"])
            except ValidationError as exc:
                issues.extend(_pydantic_issues(f"{path}.data", exc))
        elif event["event_type"] == "ALERT_CREATED":
            data = event["data"]
            try:
                Alert(
                    alert_id=data["alert_id"],
                    priority=data["priority"],
                    tracks=data.get("tracks", []),
                    threatened_zone=data.get("threatened_zone"),
                    estimated_eta_s=data.get("estimated_eta_s"),
                    message=data["message"],
                    timestamp_s=event["t_s"],
                )
            except (KeyError, ValidationError) as exc:
                issues.append(ValidationIssue(f"{path}.data", str(exc)))
    if "events" not in raw:
        issues.append(ValidationIssue("$.events", "missing required events array"))
    if issues:
        raise NeonDataValidationError(source, issues)
