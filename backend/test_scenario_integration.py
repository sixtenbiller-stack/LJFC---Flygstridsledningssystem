"""Integration tests for the minimal scenario/data path."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scenario_registry import discover, load_scenario_raw
from scenario_engine import ScenarioEngine
from data_loader import load_scenario


def test_registry_default_exposes_only_minimal():
    entries = discover()
    assert [e["file_id"] for e in entries] == ["scenario_minimal_alpha"]
    assert entries[0]["title"] == "Minimal Two-Track Decision"
    assert entries[0]["validation_status"] == "valid"


def test_load_scenario_raw_minimal():
    raw = load_scenario_raw("scenario_minimal_alpha")
    assert raw["schema_version"] == "neon.scenario.v1"
    assert raw["meta"]["scenario_id"] == "scenario_minimal_alpha"
    assert len([e for e in raw["events"] if e["event_type"] == "TRACK_CREATED"]) == 2


def test_data_loader_default_is_minimal():
    raw = load_scenario()
    assert raw["meta"]["scenario_id"] == "scenario_minimal_alpha"


def test_engine_loads_minimal_and_applies_decision_point():
    eng = ScenarioEngine()
    eng.load("scenario_minimal_alpha")
    eng.current_time_s = 35
    eng._apply_events()
    state = eng.get_state()
    assert state.scenario_id == "scenario_minimal_alpha"
    assert len(state.tracks) == 2
    assert state.coa_trigger_pending is True
