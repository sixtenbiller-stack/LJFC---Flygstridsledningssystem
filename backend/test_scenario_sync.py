"""Tests for the minimal one-scenario NEON COMMAND path."""
from pathlib import Path
import json
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_validation import validate_assets_data, validate_geography_data, validate_scenario_data, validate_scoring_params_data


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


def _load(name: str) -> dict:
    return json.loads((Path(__file__).resolve().parent.parent / "neon-command-data" / name).read_text())


class TestMinimalValidation:
    def test_minimal_geography_validates(self):
        validate_geography_data(_load("geography.json"))

    def test_minimal_assets_validates(self):
        validate_assets_data(_load("assets.json"))

    def test_minimal_scoring_validates(self):
        validate_scoring_params_data(_load("scoring_params.json"))

    def test_minimal_scenario_validates(self):
        validate_scenario_data(_load("scenario_minimal_alpha.json"))


class TestMinimalScenarioRuntime:
    def test_scenarios_default_only_minimal(self, client):
        res = client.get("/scenarios").json()
        assert res["feature_flags"]["extended_scenarios"] is False
        assert res["feature_flags"]["live_mutation"] is False
        assert res["feature_flags"]["scenario_generator"] is False
        assert [s["file_id"] for s in res["scenarios"]] == ["scenario_minimal_alpha"]

    def test_extended_scenario_rejected_by_default(self, client):
        res = client.post("/scenario/load", json={"scenario_id": "scenario_swarm_beta"})
        assert res.status_code == 403

    def test_minimal_scenario_loads(self, client):
        res = client.post("/scenario/load", json={"scenario_id": "scenario_minimal_alpha"})
        assert res.status_code == 200
        session = client.get("/scenario/session").json()
        assert session["scenario_id"] == "scenario_minimal_alpha"
        assert session["scenario_label"] == "Minimal Two-Track Decision"
        assert session["runtime_mode"] == "replay"
        assert session["scenario_origin"] == "builtin"

    def test_minimal_reaches_two_tracks(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario_minimal_alpha"})
        jump = client.post("/scenario/seek", json={"time_s": 35}).json()
        assert jump["tracks_at_target"] == 2
        state = client.get("/state").json()
        assert len(state["tracks"]) == 2
        assert state["coa_trigger_pending"] is True

    def test_group_grp_min_01_forms(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario_minimal_alpha"})
        client.post("/scenario/seek", json={"time_s": 35})
        client.get("/state")
        groups = client.get("/groups").json()
        ids = [g["group_id"] for g in groups]
        assert "grp-min-01" in ids

    def test_markers_match_minimal_timeline(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario_minimal_alpha"})
        markers = client.get("/scenario/markers").json()
        by_type = {m["type"]: m for m in markers}
        assert by_type["first_contact"]["t_s"] == 10
        assert by_type["first_group"]["t_s"] == 25
        assert by_type["first_decision"]["t_s"] == 35

    def test_live_and_generator_disabled(self, client):
        assert client.post("/scenario/generate", json={"template": "swarm_pressure"}).status_code == 403
        assert client.post("/scenario/live/start", json={"file_id": "scenario_minimal_alpha"}).status_code == 403


class TestLocalLlmPath:
    def test_llm_situation_brief_input_is_compact(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario_minimal_alpha"})
        client.post("/scenario/seek", json={"time_s": 35})
        client.get("/state")
        snap = client.get("/llm/situation-brief/input").json()
        assert snap["schema_version"] == "neon.llm_input.v1"
        assert snap["task"] == "situation_brief"
        assert snap["scenario"]["scenario_id"] == "scenario_minimal_alpha"
        assert snap["selected_group"]["group_id"] == "grp-min-01"
        assert "events" not in snap

    def test_llm_situation_brief_output_schema_shape(self):
        schema = json.loads((Path(__file__).resolve().parent.parent / "schemas" / "llm" / "situation_brief.schema.json").read_text())
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == {"schema_version", "summary", "why_it_matters", "recommended_next_action", "confidence", "cited_ids"}
