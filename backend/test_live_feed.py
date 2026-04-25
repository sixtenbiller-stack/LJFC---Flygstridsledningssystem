"""Tests for the synthetic live-feed and visible Chief of Staff path."""
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from live_feed import SyntheticLiveFeedSource


def test_live_feed_minimal_alpha_parses():
    feed = SyntheticLiveFeedSource("live_feed_minimal_alpha")
    assert feed.events[0].event_type == "FEED_START"
    assert any(event.event_type == "TRACK_OBSERVED" for event in feed.events)
    assert any(event.event_type == "RECOMMENDATION_TRIGGERED" for event in feed.events)


def test_feed_step_applies_first_track():
    from main import app

    client = TestClient(app)
    client.post("/feed/load", json={"feed_id": "live_feed_minimal_alpha"})
    client.post("/feed/control", json={"action": "step"})
    client.post("/feed/control", json={"action": "step"})
    state = client.get("/state").json()
    assert state["feed_status"]["feed_id"] == "live_feed_minimal_alpha"
    assert any(track["track_id"] == "trk-h01" for track in state["tracks"])


def test_feed_group_and_ato_context_reach_agent_chat(monkeypatch):
    import gemini_provider
    from main import app

    def fake_generate_json(*args, **kwargs):
        return {
            "schema_version": "neon.llm.chief_of_staff_response.v1",
            "response_type": "brief",
            "bluf": "grp-min-01 is the current primary threat to city-arktholm.",
            "situation": "Two synthetic tracks share arktholm-south.",
            "evidence": [{"label": "Group", "detail": "grp-min-01 includes trk-h01 and trk-h02.", "cited_id": "grp-min-01"}],
            "recommendation": "Preserve one fighter reserve and generate bounded COAs.",
            "next_actions": [{"label": "Generate COAs", "command": "/recommend"}],
            "confidence": "medium",
            "warnings": [],
            "cited_ids": ["grp-min-01", "trk-h01", "trk-h02", "ato_minimal_alpha", "city-arktholm"],
        }

    monkeypatch.setattr(gemini_provider, "generate_json", fake_generate_json)
    client = TestClient(app)
    client.post("/feed/load", json={"feed_id": "live_feed_minimal_alpha"})
    client.post("/scenario/seek", json={"time_s": 45})
    client.get("/state")
    response = client.post("/agent/chat", json={"message": "Give me the current threat brief."}).json()
    assert response["structured"]["bluf"].startswith("grp-min-01")
    assert response["structured"]["cited_ids"]
    assert response["provider"] in {"ollama", "gemini", "mock"}
