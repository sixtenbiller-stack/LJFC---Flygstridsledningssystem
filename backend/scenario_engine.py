"""Scenario playback engine — deterministic event-driven state machine."""
from __future__ import annotations

import asyncio
import copy
import math
import time
from typing import Any

from models import (
    Asset, Track, Alert, PathPoint, ScenarioEvent, ScenarioState, Point,
)
from data_loader import load_geography, load_assets, load_scenario, load_scenario_events


class ScenarioEngine:
    def __init__(self) -> None:
        self._scenario_id: str = ""
        self._scenario_name: str = ""
        self._events: list[ScenarioEvent] = []
        self._duration_s: float = 240

        self.current_time_s: float = 0.0
        self.is_playing: bool = False
        self.speed_multiplier: float = 1.0

        self.tracks: dict[str, Track] = {}
        self.assets: dict[str, Asset] = {}
        self.alerts: list[Alert] = []
        self.events_log: list[dict[str, Any]] = []
        self.geography = None

        self._initial_assets: list[Asset] = []
        self._events_applied_up_to: int = 0
        self._last_tick: float = 0.0
        self._wave: int = 0
        self._coa_trigger_pending: bool = False
        self._approved_coas: list[str] = []
        self._committed_assets: set[str] = set()
        self._sensor_states: dict[str, dict] = {}
        self._scenario_meta: dict = {}

        self._tick_task: asyncio.Task | None = None

    @property
    def wave(self) -> int:
        return self._wave

    @property
    def coa_trigger_pending(self) -> bool:
        return self._coa_trigger_pending

    def clear_coa_trigger(self) -> None:
        self._coa_trigger_pending = False

    @property
    def source_state_id(self) -> str:
        t = int(self.current_time_s)
        return f"snap-{self._scenario_id}-t{t}"

    @property
    def sensor_states(self) -> dict[str, dict]:
        return dict(self._sensor_states)

    @property
    def scenario_meta(self) -> dict:
        return dict(self._scenario_meta)

    def load(self, scenario_id: str = "scenario-alpha") -> None:
        raw = load_scenario(scenario_id)
        self._load_from_raw(scenario_id, raw)

    def load_from_data(self, scenario_id: str, raw: dict) -> None:
        """Load from an already-parsed dict (generated / runtime scenarios)."""
        self._load_from_raw(scenario_id, raw)

    def _load_from_raw(self, scenario_id: str, raw: dict) -> None:
        self._scenario_id = scenario_id
        self._scenario_meta = raw.get("meta", {})
        self._scenario_name = self._scenario_meta.get("name", scenario_id)
        self._duration_s = self._scenario_meta.get("duration_s", 240)
        self._events = [ScenarioEvent(**e) for e in raw["events"]]
        self.geography = load_geography()

        initial_assets = load_assets()
        self._initial_assets = initial_assets
        self.assets = {a.asset_id: copy.deepcopy(a) for a in initial_assets}

        self.tracks = {}
        self.alerts = []
        self.events_log = []
        self.current_time_s = 0.0
        self._events_applied_up_to = 0
        self._wave = 0
        self._coa_trigger_pending = False
        self._approved_coas = []
        self._committed_assets = set()
        self._sensor_states = {}
        self.is_playing = False
        self.speed_multiplier = 1.0
        self._last_tick = time.monotonic()

    def reset(self) -> None:
        if self._scenario_id:
            self.load(self._scenario_id)

    def play(self) -> None:
        self.is_playing = True
        self._last_tick = time.monotonic()

    def pause(self) -> None:
        self.is_playing = False

    def set_speed(self, speed: float) -> None:
        self.speed_multiplier = max(0.5, min(speed, 8.0))

    def commit_assets(self, asset_ids: list[str]) -> None:
        """Mark assets as committed after COA approval."""
        for aid in asset_ids:
            self._committed_assets.add(aid)
            if aid in self.assets:
                asset = self.assets[aid]
                asset.status = "active"
                asset.current_assignment = "wave_response"
                asset.readiness = max(0.0, asset.readiness - 0.3)

    def tick(self) -> None:
        """Advance scenario time and apply pending events."""
        if not self.is_playing:
            return

        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now
        self.current_time_s += dt * self.speed_multiplier
        if self.current_time_s > self._duration_s:
            self.current_time_s = self._duration_s
            self.is_playing = False

        self._apply_events()
        self._interpolate_tracks()

    def _apply_events(self) -> None:
        while self._events_applied_up_to < len(self._events):
            ev = self._events[self._events_applied_up_to]
            if ev.t_s > self.current_time_s:
                break
            self._process_event(ev)
            self._events_applied_up_to += 1

    def _process_event(self, ev: ScenarioEvent) -> None:
        data = ev.data
        etype = ev.event_type

        log_entry = {"t_s": ev.t_s, "type": etype, "summary": data.get("message", data.get("notes", etype))}
        self.events_log.append(log_entry)

        if etype == "SCENARIO_START":
            self._wave = 0

        elif etype == "TRACK_CREATED":
            predicted = [PathPoint(**p) for p in data.get("predicted_path", [])]
            track = Track(
                track_id=data["track_id"],
                side=data.get("side", "hostile"),
                class_label=data.get("class_label", "unknown"),
                confidence=data.get("confidence", 0.5),
                x_km=data["x_km"],
                y_km=data["y_km"],
                heading_deg=data.get("heading_deg", 0),
                speed_class=data.get("speed_class", "medium"),
                altitude_band=data.get("altitude_band", "medium"),
                detected_by=data.get("detected_by", []),
                predicted_path=predicted,
                notes=data.get("notes"),
                corridor_id=data.get("corridor_id"),
                group_seed_id=data.get("group_seed_id"),
                formation_hint=data.get("formation_hint"),
                decoy_probability=data.get("decoy_probability"),
                signature_hint=data.get("signature_hint"),
                payload_known=data.get("payload_known"),
                payload_type=data.get("payload_type"),
                rf_emitting=data.get("rf_emitting"),
                maneuver_pattern=data.get("maneuver_pattern"),
                source_disagreement=data.get("source_disagreement"),
            )
            self.tracks[track.track_id] = track
            if ev.t_s >= 90 and self._wave < 2:
                self._wave = 2

        elif etype == "TRACK_UPDATED":
            tid = data["track_id"]
            if tid in self.tracks:
                t = self.tracks[tid]
                updates = data.get("updates", {})
                if "confidence" in updates:
                    t.confidence = updates["confidence"]
                if "x_km" in updates:
                    t.x_km = updates["x_km"]
                if "y_km" in updates:
                    t.y_km = updates["y_km"]
                if "altitude_band" in updates:
                    t.altitude_band = updates["altitude_band"]
                if "class_label" in updates:
                    t.class_label = updates["class_label"]
                if data.get("notes"):
                    t.notes = data["notes"]

        elif etype == "ALERT_CREATED":
            alert = Alert(
                alert_id=data["alert_id"],
                priority=data["priority"],
                tracks=data.get("tracks", []),
                threatened_zone=data.get("threatened_zone"),
                estimated_eta_s=data.get("estimated_eta_s"),
                message=data["message"],
                timestamp_s=ev.t_s,
            )
            self.alerts.append(alert)

        elif etype == "COA_TRIGGER":
            self._coa_trigger_pending = True
            if self._wave < 1:
                self._wave = 1

        elif etype == "GROUP_FORMED":
            pass  # groups tracked via track metadata + ThreatGroupEngine

        elif etype == "SENSOR_DEGRADED":
            sid = data.get("sensor_id")
            severity = data.get("severity", "degraded")
            self._sensor_states[sid] = {
                "status": severity,
                "range_multiplier": data.get("detection_range_multiplier", 0.5),
                "since_t_s": ev.t_s,
            }

        elif etype == "TRACK_LOST":
            tid = data.get("track_id")
            if tid and tid in self.tracks:
                self.tracks[tid].status = "lost"

        elif etype == "CONSTRAINT_CHANGED":
            if self._committed_assets:
                for aid in self._committed_assets:
                    if aid in self.assets:
                        a = self.assets[aid]
                        a.status = "recovering"
                        a.readiness = max(0.0, a.readiness - 0.2)
                        a.recovery_eta_min = 25
                        a.availability_reason = "wave_1_recovery"

        elif etype == "SCENARIO_END":
            self.is_playing = False

    def _interpolate_tracks(self) -> None:
        """Interpolate track positions along predicted paths based on current time."""
        for track in self.tracks.values():
            if track.status != "active" or not track.predicted_path:
                continue
            path = track.predicted_path
            if self.current_time_s <= path[0].t_s:
                continue
            if self.current_time_s >= path[-1].t_s:
                track.x_km = path[-1].x_km
                track.y_km = path[-1].y_km
                continue
            for i in range(len(path) - 1):
                if path[i].t_s <= self.current_time_s <= path[i + 1].t_s:
                    frac = (self.current_time_s - path[i].t_s) / (path[i + 1].t_s - path[i].t_s)
                    track.x_km = path[i].x_km + frac * (path[i + 1].x_km - path[i].x_km)
                    track.y_km = path[i].y_km + frac * (path[i + 1].y_km - path[i].y_km)
                    break

    def get_state(self, include_geo: bool = False) -> ScenarioState:
        return ScenarioState(
            scenario_id=self._scenario_id,
            scenario_name=self._scenario_name,
            current_time_s=round(self.current_time_s, 1),
            is_playing=self.is_playing,
            speed_multiplier=self.speed_multiplier,
            source_state_id=self.source_state_id,
            tracks=list(self.tracks.values()),
            assets=list(self.assets.values()),
            alerts=self.alerts,
            geography=self.geography if include_geo else None,
            wave=self._wave,
            coa_trigger_pending=self._coa_trigger_pending,
            events_log=self.events_log[-50:],
            scenario_meta=self._scenario_meta,
            sensor_states=self._sensor_states,
        )

    async def start_ticker(self, interval: float = 0.1) -> None:
        """Background loop that ticks the engine."""
        while True:
            self.tick()
            await asyncio.sleep(interval)
