"""Tests for scenario synchronization, mode/origin separation, operator markers, and session management."""
import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "neon-command-engine"))


@pytest.fixture(scope="module")
def client():
    from main import app
    return TestClient(app)


class TestModeOriginSeparation:
    """runtime_mode and scenario_origin must be separate concepts."""

    def test_alpha_is_replay_builtin(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        s = client.get("/scenario/session").json()
        assert s["runtime_mode"] == "replay"
        assert s["scenario_origin"] == "builtin"

    def test_swarm_beta_is_replay_generated(self, client):
        """swarm_beta has generator metadata — origin is generated, but mode is replay."""
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        s = client.get("/scenario/session").json()
        assert s["runtime_mode"] == "replay", "Should be replay, not 'generated'"
        assert s["scenario_origin"] == "generated"

    def test_raid_gamma_is_replay_generated(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-raid-gamma"})
        s = client.get("/scenario/session").json()
        assert s["runtime_mode"] == "replay"
        assert s["scenario_origin"] == "generated"

    def test_live_session_is_live_runtime_copy(self, client):
        client.post("/scenario/live/start", json={"file_id": "scenario_swarm_beta"})
        s = client.get("/scenario/session").json()
        assert s["runtime_mode"] == "live"
        assert s["scenario_origin"] == "runtime_copy"
        assert s["source_parent_scenario"] == "scenario_swarm_beta"
        assert s["runtime_session_id"] is not None

    def test_state_endpoint_also_has_both_fields(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        state = client.get("/state").json()
        assert state["runtime_mode"] == "replay"
        assert state["scenario_origin"] == "generated"
        assert state["mode"] == "replay"

    def test_live_to_replay_resets_origin(self, client):
        client.post("/scenario/live/start", json={"file_id": "scenario_swarm_beta"})
        s1 = client.get("/scenario/session").json()
        assert s1["runtime_mode"] == "live"
        assert s1["scenario_origin"] == "runtime_copy"

        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        s2 = client.get("/scenario/session").json()
        assert s2["runtime_mode"] == "replay"
        assert s2["scenario_origin"] == "builtin"
        assert s2["runtime_session_id"] is None
        assert s2["source_parent_scenario"] is None


class TestOperatorMomentMarkers:
    """Markers must reflect operator-visible moments, not raw event order."""

    def test_first_group_visible_not_before_first_contact(self, client):
        """In swarm_beta, GROUP_FORMED is at t=12 but TRACK_CREATED at t=18.
        first_group marker must be >= first_contact marker."""
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        markers = client.get("/scenario/markers").json()
        by_type = {m["type"]: m for m in markers}
        assert "first_contact" in by_type
        assert "first_group" in by_type
        assert by_type["first_group"]["t_s"] >= by_type["first_contact"]["t_s"], \
            f"first_group ({by_type['first_group']['t_s']}) should be >= first_contact ({by_type['first_contact']['t_s']})"

    def test_first_decision_not_before_first_contact(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        markers = client.get("/scenario/markers").json()
        by_type = {m["type"]: m for m in markers}
        if "first_decision" in by_type and "first_contact" in by_type:
            assert by_type["first_decision"]["t_s"] >= by_type["first_contact"]["t_s"]

    def test_alpha_markers_in_order(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        markers = client.get("/scenario/markers").json()
        times = [m["t_s"] for m in markers]
        assert times == sorted(times), "Markers must be sorted by time"
        types = [m["type"] for m in markers]
        assert "first_contact" in types

    def test_swarm_beta_has_sensor_degraded(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        markers = client.get("/scenario/markers").json()
        types = [m["type"] for m in markers]
        assert "sensor_degraded" in types


class TestJumpLandsOnMeaningfulState:

    def test_jump_first_contact_has_tracks(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        r = client.post("/scenario/jump", json={"target": "first_contact"}).json()
        assert r["status"] == "jumped"
        assert r["tracks_at_target"] > 0

    def test_jump_first_group_has_tracks(self, client):
        """After jumping to first_group, tracks should be visible."""
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        r = client.post("/scenario/jump", json={"target": "first_group"}).json()
        assert r["status"] == "jumped"
        assert r["tracks_at_target"] > 0, "first_group jump should land after first tracks are visible"

    def test_jump_uses_derived_markers_not_raw(self, client):
        """Jump to first_group should use the derived marker time, not the raw GROUP_FORMED time."""
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        markers = client.get("/scenario/markers").json()
        by_type = {m["type"]: m for m in markers}
        r = client.post("/scenario/jump", json={"target": "first_group"}).json()
        assert r["time_s"] == by_type["first_group"]["t_s"]

    def test_jump_invalid_target(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        r = client.post("/scenario/jump", json={"target": "nonexistent"}).json()
        assert "error" in r


class TestSeek:

    def test_seek_to_middle(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        r = client.post("/scenario/seek", json={"time_s": 60}).json()
        assert r["status"] == "seeked"
        assert r["time_s"] == 60.0
        assert r["tracks_at_target"] > 0

    def test_seek_clamped_to_duration(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        r = client.post("/scenario/seek", json={"time_s": 9999}).json()
        assert r["time_s"] <= 240


class TestScenarioSwitchClearsState:

    def test_switch_clears_stale_data(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        client.post("/scenario/jump", json={"target": "first_contact"})

        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        state = client.get("/state").json()
        assert state["scenario_id"] == "scenario-swarm-beta"
        assert state["current_time_s"] == 0.0

    def test_source_state_id_resets(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        client.post("/scenario/jump", json={"target": "first_contact"})
        sid1 = client.get("/scenario/session").json()["source_state_id"]

        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        sid2 = client.get("/scenario/session").json()["source_state_id"]
        assert "scenario-swarm-beta" in sid2
        assert sid1 != sid2


class TestCopilotScenarioCommands:

    def test_scenario_command_shows_mode_and_origin(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        r = client.post("/copilot/command", json={"input": "/scenario"}).json()
        assert "REPLAY" in r["message"]
        assert "GENERATED" in r["message"]

    def test_mode_command_shows_replay(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        r = client.post("/copilot/command", json={"input": "/mode"}).json()
        assert "REPLAY" in r["message"]
        assert "BUILTIN" in r["message"]

    def test_live_status_when_not_live(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        r = client.post("/copilot/command", json={"input": "/live-status"}).json()
        assert "not" in r["message"].lower() or "Not" in r["message"]

    def test_jump_command(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        r = client.post("/copilot/command", json={"input": "/jump first-contact"}).json()
        assert "Jump" in r["message"] or "jump" in r["message"]


class TestMutationLog:

    def test_mutation_log_in_session(self, client):
        client.post("/scenario/live/start", json={"file_id": "scenario_swarm_beta"})
        s = client.get("/scenario/session").json()
        assert "mutation_log" in s
        assert isinstance(s["mutation_log"], list)


class TestSessionMetadata:

    def test_session_has_all_required_fields(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        s = client.get("/scenario/session").json()
        required = ["scenario_id", "scenario_label", "source_file", "runtime_mode",
                     "scenario_origin", "source_state_id", "duration_s", "current_time_s",
                     "status", "is_playing", "track_count", "group_count",
                     "extended_schema_present", "loaded_at", "wave"]
        for f in required:
            assert f in s, f"Missing field: {f}"

    def test_extended_schema_present_for_beta(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-swarm-beta"})
        s = client.get("/scenario/session").json()
        assert s["extended_schema_present"] is True

    def test_no_extended_schema_for_alpha(self, client):
        client.post("/scenario/load", json={"scenario_id": "scenario-alpha"})
        s = client.get("/scenario/session").json()
        assert s["extended_schema_present"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
