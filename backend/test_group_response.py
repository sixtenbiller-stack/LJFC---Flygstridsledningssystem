"""Tests for threat grouping, response ranking, lane assignment, and decision flow."""
import json
import pytest
from pathlib import Path

from models import Track, DefendedZone, Asset, ThreatGroup, ResponseOption, AfterActionRecord
from threat_scorer import ThreatScorer
from threat_group_engine import ThreatGroupEngine
from response_ranking_engine import ResponseRankingEngine

DATA_DIR = Path(__file__).resolve().parent.parent / "neon-command-data"


def _load_scenario_tracks():
    with open(DATA_DIR / "scenario_alpha.json") as f:
        scenario = json.load(f)
    tracks, ct = [], {}
    for evt in scenario["events"]:
        if evt["event_type"] == "TRACK_CREATED":
            d = evt["data"]
            safe = {k: v for k, v in d.items() if k not in ("notes", "predicted_path")}
            tracks.append(Track(**safe))
            ct[d["track_id"]] = evt["t_s"]
    return tracks, ct


def _load_zones():
    with open(DATA_DIR / "geography.json") as f:
        geo = json.load(f)
    return [DefendedZone(**z) for z in geo["defended_zones"]]


def _load_assets():
    with open(DATA_DIR / "assets.json") as f:
        raw = json.load(f)
    return [Asset(**a) for a in raw["assets"]]


@pytest.fixture
def tracks_and_times():
    return _load_scenario_tracks()


@pytest.fixture
def zones():
    return _load_zones()


@pytest.fixture
def assets():
    return _load_assets()


@pytest.fixture
def scorer():
    return ThreatScorer()


@pytest.fixture
def grouper():
    return ThreatGroupEngine()


@pytest.fixture
def ranker():
    return ResponseRankingEngine()


class TestGroupFormation:
    def test_scenario_alpha_produces_two_groups(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        assert len(groups) == 2

    def test_wave1_group_has_3_tracks(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        wave1_ids = {"trk-h01", "trk-h02", "trk-h03"}
        wave1_group = [g for g in groups if set(g.member_track_ids) == wave1_ids]
        assert len(wave1_group) == 1

    def test_wave2_group_has_5_tracks(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        wave2_ids = {"trk-h04", "trk-h05", "trk-h06", "trk-h07", "trk-h08"}
        wave2_group = [g for g in groups if set(g.member_track_ids) == wave2_ids]
        assert len(wave2_group) == 1

    def test_groups_sorted_by_urgency(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        if len(groups) >= 2:
            assert groups[0].urgency_score >= groups[1].urgency_score

    def test_coordination_score_positive(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        for g in groups:
            assert g.coordination_score >= 0

    def test_group_has_rationale(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        for g in groups:
            assert len(g.rationale) >= 1

    def test_group_has_narration(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        for g in groups:
            assert len(g.short_narration) > 10


class TestLaneAssignment:
    def test_wave2_is_fast_lane(self, tracks_and_times, zones, scorer, grouper):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        wave2 = [g for g in groups if len(g.member_track_ids) == 5]
        assert len(wave2) == 1
        assert wave2[0].recommended_lane == "fast"

    def test_low_confidence_triggers_slow_lane(self, zones, scorer, grouper):
        low_conf_tracks = [
            Track(track_id="t1", x_km=200, y_km=580, heading_deg=190, confidence=0.3, speed_class="medium"),
            Track(track_id="t2", x_km=210, y_km=575, heading_deg=195, confidence=0.35, speed_class="medium"),
        ]
        scores = scorer.score_all(low_conf_tracks, zones, 60.0)
        ct = {"t1": 0, "t2": 5}
        groups = grouper.assess(low_conf_tracks, zones, scores, 60.0, "sid", ct)
        for g in groups:
            assert g.recommended_lane == "slow"


class TestResponseRanking:
    def test_returns_at_least_3_options(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        for g in groups:
            responses = ranker.rank(g, assets)
            assert len(responses) >= 3

    def test_responses_sorted_by_rank(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        for g in groups:
            responses = ranker.rank(g, assets)
            for i in range(len(responses) - 1):
                assert responses[i].rank < responses[i + 1].rank

    def test_swarm_group_favors_non_kinetic(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        swarm = [g for g in groups if "swarm" in g.group_type]
        if swarm:
            responses = ranker.rank(swarm[0], assets)
            top_families = [r.response_family for r in responses[:3]]
            assert "non_kinetic_disrupt_synthetic" in top_families or "observe_verify" in top_families

    def test_responses_have_scoring_factors(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        responses = ranker.rank(groups[0], assets)
        for r in responses:
            assert len(r.scoring_factors) > 0

    def test_authority_gating(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        responses = ranker.rank(groups[0], assets)
        escalate = [r for r in responses if r.response_family == "escalate_command_review"]
        if escalate:
            assert escalate[0].authority_required == "needs_confirmation"


class TestDecisionSnapshot:
    def test_decision_card_builds(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        from models import DecisionCardSnapshot
        import datetime

        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        g = groups[0]
        responses = ranker.rank(g, assets)

        card = DecisionCardSnapshot(
            card_id=f"card-{g.group_id}",
            group_id=g.group_id,
            group=g,
            recommended_response=responses[0],
            alternatives=responses[1:3],
            authority_status=responses[0].authority_required,
            source_state_id="sid-test",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        )
        assert card.card_id.startswith("card-")
        assert card.recommended_response.rank == 1
        assert len(card.alternatives) == 2


class TestAfterActionRecord:
    def test_after_action_creation(self, tracks_and_times, zones, scorer, grouper, ranker, assets):
        import datetime
        tracks, ct = tracks_and_times
        scores = scorer.score_all(tracks, zones, 120.0)
        groups = grouper.assess(tracks, zones, scores, 120.0, "sid-test", ct)
        g = groups[0]
        responses = ranker.rank(g, assets)

        record = AfterActionRecord(
            record_id="aar-001",
            timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            group_id=g.group_id,
            group_snapshot=g.model_dump(),
            response_chosen=responses[0].response_id,
            response_family=responses[0].response_family,
            operator_action="approve",
            source_state_id="sid-test",
            wave=2,
        )
        assert record.operator_action == "approve"
        assert record.group_id == g.group_id
