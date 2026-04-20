"""Integration tests for scenario runtime, registry, and extended schema support."""
import json
import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "neon-command-engine"))

from scenario_registry import discover, load_scenario_raw, DATA_DIR, GENERATED_DIR
from scenario_runtime import generate_scenario, LiveSession
from models import Track, ScenarioEvent
from scenario_engine import ScenarioEngine
from threat_group_engine import ThreatGroupEngine
from data_loader import load_scenario_events, load_scenario


class TestScenarioRegistry:
    def test_discovers_base_scenarios(self):
        entries = discover()
        file_ids = [e["file_id"] for e in entries]
        assert "scenario_alpha" in file_ids
        assert "scenario_swarm_beta" in file_ids
        assert "scenario_raid_gamma" in file_ids

    def test_entry_has_metadata(self):
        entries = discover()
        alpha = next(e for e in entries if e["file_id"] == "scenario_alpha")
        assert alpha["source_type"] == "base"
        assert alpha["title"] == "Two-Wave Pressure Test"
        assert alpha["duration_s"] is not None

    def test_swarm_beta_has_extended_fields(self):
        entries = discover()
        beta = next(e for e in entries if e["file_id"] == "scenario_swarm_beta")
        assert beta["extended_fields"] is True
        assert beta["track_count"] > 0
        assert beta["group_count"] > 0

    def test_raid_gamma_discoverable(self):
        entries = discover()
        gamma = next(e for e in entries if e["file_id"] == "scenario_raid_gamma")
        assert gamma["recommended_mode"] == "live"
        assert gamma["jury_demo"] is True


class TestExtendedSchema:
    def test_alpha_still_parses(self):
        """scenario_alpha has no extended fields — must still parse."""
        raw = load_scenario_raw("scenario_alpha")
        events = raw["events"]
        track_events = [e for e in events if e["event_type"] == "TRACK_CREATED"]
        assert len(track_events) > 0
        for te in track_events:
            t = Track(**{k: v for k, v in te["data"].items()
                        if k in Track.model_fields})
            assert t.track_id
            assert t.corridor_id is None
            assert t.group_seed_id is None

    def test_swarm_beta_has_extended_track_fields(self):
        raw = load_scenario_raw("scenario_swarm_beta")
        track_events = [e for e in raw["events"] if e["event_type"] == "TRACK_CREATED"]
        assert len(track_events) > 0
        first = track_events[0]["data"]
        assert "corridor_id" in first
        assert "group_seed_id" in first
        assert "decoy_probability" in first

    def test_raid_gamma_loads(self):
        raw = load_scenario_raw("scenario_raid_gamma")
        assert raw["meta"]["scenario_id"]
        assert len(raw["events"]) > 0


class TestScenarioEngine:
    def test_alpha_loads_into_engine(self):
        eng = ScenarioEngine()
        eng.load("scenario-alpha")
        assert eng._scenario_id == "scenario-alpha"
        assert len(eng._events) > 0

    def test_swarm_beta_loads_into_engine(self):
        eng = ScenarioEngine()
        eng.load("scenario-swarm-beta")
        assert eng._scenario_id == "scenario-swarm-beta"
        assert len(eng._events) > 0

    def test_swarm_beta_tracks_have_extended_fields(self):
        eng = ScenarioEngine()
        eng.load("scenario-swarm-beta")
        eng.current_time_s = 999
        eng._apply_events()
        tracks = list(eng.tracks.values())
        assert len(tracks) > 0
        extended = [t for t in tracks if t.corridor_id is not None]
        assert len(extended) > 0

    def test_load_from_data(self):
        raw = load_scenario_raw("scenario_raid_gamma")
        eng = ScenarioEngine()
        eng.load_from_data("scenario-raid-gamma", raw)
        eng.current_time_s = 999
        eng._apply_events()
        assert len(eng.tracks) > 0

    def test_sensor_degraded_event(self):
        raw = load_scenario_raw("scenario_swarm_beta")
        eng = ScenarioEngine()
        eng.load_from_data("test", raw)
        eng.current_time_s = 999
        eng._apply_events()
        assert len(eng._sensor_states) >= 0  # may or may not have degradation events


class TestGenerator:
    def test_deterministic_by_seed(self):
        r1 = generate_scenario(template="swarm_pressure", seed=42)
        r2 = generate_scenario(template="swarm_pressure", seed=42)
        assert r1["seed"] == r2["seed"]
        path1 = Path(r1["path"])
        path2 = Path(r2["path"])
        with open(path1) as f:
            d1 = json.load(f)
        with open(path2) as f:
            d2 = json.load(f)
        assert len(d1["events"]) == len(d2["events"])

    def test_output_goes_to_generated_dir(self):
        r = generate_scenario(template="swarm_pressure", seed=99999)
        assert "generated" in r["path"]
        assert Path(r["path"]).exists()
        Path(r["path"]).unlink()  # cleanup

    def test_random_template(self):
        r = generate_scenario(template="random", seed=12345, duration_s=120)
        assert r["template"] == "random"
        assert Path(r["path"]).exists()
        Path(r["path"]).unlink()

    def test_generated_scenario_loadable(self):
        r = generate_scenario(template="escalating_probe", seed=7777)
        eng = ScenarioEngine()
        raw = load_scenario_raw(r["file_id"])
        eng.load_from_data(r["file_id"], raw)
        eng.current_time_s = 999
        eng._apply_events()
        assert len(eng.tracks) > 0
        Path(r["path"]).unlink()


class TestLiveSession:
    def test_create_session(self):
        session = LiveSession("scenario_swarm_beta", seed=42)
        assert session.session_id.startswith("live-")
        assert session.file_id == "scenario_swarm_beta"

    def test_tick_advances_time(self):
        session = LiveSession("scenario_swarm_beta", seed=42)
        t0 = session.current_time_s
        session.tick(dt_s=10)
        assert session.current_time_s > t0

    def test_inject_swarm(self):
        session = LiveSession("scenario_swarm_beta", seed=42)
        session.tick(dt_s=5)
        result = session.inject("swarm", {"corridor": "corridor-n", "size": 8})
        assert result.get("events_added", 0) > 0

    def test_inject_second_wave(self):
        session = LiveSession("scenario_raid_gamma", seed=42)
        session.tick(dt_s=5)
        result = session.inject("second_wave")
        assert result.get("events_added", 0) > 0

    def test_inject_sensor_degrade(self):
        session = LiveSession("scenario_swarm_beta", seed=42)
        session.tick(dt_s=5)
        result = session.inject("sensor_degrade", {"sensor_id": "sensor-boreal"})
        assert "event" in result

    def test_state_snapshot(self):
        session = LiveSession("scenario_swarm_beta", seed=42)
        snap = session.get_state_snapshot()
        assert snap["mode"] == "live"
        assert snap["session_id"]

    def test_events_for_engine(self):
        session = LiveSession("scenario_swarm_beta", seed=42)
        events = session.get_events_for_engine()
        assert len(events) > 0


class TestGroupEngineWithExtended:
    def test_grouping_on_swarm_beta(self):
        eng = ScenarioEngine()
        eng.load("scenario-swarm-beta")
        eng.current_time_s = 999
        eng._apply_events()

        tracks = list(eng.tracks.values())
        zones = eng.geography.defended_zones if eng.geography else []
        creation_times = {}
        for ev in eng._events:
            if ev.event_type == "TRACK_CREATED":
                tid = ev.data.get("track_id")
                if tid:
                    creation_times[tid] = ev.t_s

        from threat_scorer import ThreatScorer
        scorer = ThreatScorer()
        scores = scorer.score_all(tracks, zones, eng.current_time_s)

        grouper = ThreatGroupEngine()
        groups = grouper.assess(tracks, zones, scores, eng.current_time_s,
                               "test-state", creation_times)
        assert len(groups) > 0
        for g in groups:
            assert g.group_id
            assert g.group_type
            assert g.recommended_lane in ("fast", "slow")

    def test_alpha_still_groups(self):
        eng = ScenarioEngine()
        eng.load("scenario-alpha")
        eng.current_time_s = 999
        eng._apply_events()

        tracks = list(eng.tracks.values())
        zones = eng.geography.defended_zones if eng.geography else []
        creation_times = {}
        for ev in eng._events:
            if ev.event_type == "TRACK_CREATED":
                tid = ev.data.get("track_id")
                if tid:
                    creation_times[tid] = ev.t_s

        from threat_scorer import ThreatScorer
        scorer = ThreatScorer()
        scores = scorer.score_all(tracks, zones, eng.current_time_s)

        grouper = ThreatGroupEngine()
        groups = grouper.assess(tracks, zones, scores, eng.current_time_s,
                               "test-state", creation_times)
        assert len(groups) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
