"""
LJFC COMMAND — Scenario Generator Module
=========================================
Produces randomized but tactically coherent air defence scenarios.

This module generates scenarios that exercise:
- Coordinated multi-track threats (swarms, raids, probes)
- Decoy discrimination
- Mixed threat types at different speeds and altitudes
- Degraded sensor data and source disagreement
- Second/third wave pressure after resource commitment
- Group-level reasoning (not just individual track thinking)

Usage:
    from scenario_generator import ScenarioGenerator
    gen = ScenarioGenerator(seed=42)
    scenario = gen.generate(template="swarm_pressure")
    scenario.to_json("scenario_output.json")

The output is a JSON file compatible with the LJFC COMMAND scenario engine,
extended with group-aware fields for the Threat Assessment Engine.
"""

import json
import math
import random
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from pathlib import Path


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Side(str, Enum):
    HOSTILE = "hostile"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class TrackClass(str, Enum):
    FIGHTER = "fighter-type"
    CRUISE = "cruise-type"
    UAV_RECON = "uav-recon"
    UAV_ARMED = "uav-armed"
    UAV_SWARM = "uav-swarm"
    DECOY = "decoy-suspected"
    JAMMER = "ew-jammer"
    UNKNOWN = "unknown"


class SpeedClass(str, Enum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class AltitudeBand(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ThreatGroupType(str, Enum):
    SINGLE_INBOUND = "single_inbound"
    COORDINATED_PROBE = "coordinated_probe"
    PROBABLE_SWARM = "probable_swarm"
    MIXED_RAID_WITH_DECOYS = "mixed_raid_with_decoys"
    SECOND_WAVE_PRESSURE = "second_wave_pressure"
    RECON_OR_DECOY_SCREEN = "recon_or_decoy_screen"


class WorkflowLane(str, Enum):
    FAST = "FAST"
    SLOW = "SLOW"


class EventType(str, Enum):
    SCENARIO_START = "SCENARIO_START"
    TRACK_CREATED = "TRACK_CREATED"
    TRACK_UPDATED = "TRACK_UPDATED"
    TRACK_LOST = "TRACK_LOST"
    ALERT_CREATED = "ALERT_CREATED"
    COA_TRIGGER = "COA_TRIGGER"
    GROUP_FORMED = "GROUP_FORMED"
    GROUP_UPDATED = "GROUP_UPDATED"
    CONSTRAINT_CHANGED = "CONSTRAINT_CHANGED"
    SENSOR_DEGRADED = "SENSOR_DEGRADED"
    SCENARIO_END = "SCENARIO_END"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Waypoint:
    t_s: int
    x_km: float
    y_km: float


@dataclass
class TrackEvent:
    track_id: str
    side: str
    class_label: str
    confidence: float
    x_km: float
    y_km: float
    heading_deg: float
    speed_class: str
    altitude_band: str
    detected_by: list
    predicted_path: list = field(default_factory=list)
    notes: str = ""
    # Extended group-aware fields
    corridor_id: Optional[str] = None
    signature_hint: Optional[str] = None
    decoy_probability: Optional[float] = None
    formation_hint: Optional[str] = None
    source_disagreement: Optional[bool] = None
    group_seed_id: Optional[str] = None
    payload_known: Optional[bool] = None
    payload_type: Optional[str] = None
    rf_emitting: Optional[bool] = None
    maneuver_pattern: Optional[str] = None


@dataclass
class ScenarioEvent:
    t_s: int
    event_type: str
    data: dict


@dataclass
class Scenario:
    meta: dict
    initial_state: dict
    events: list

    def to_json(self, path: str, indent: int = 2):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=indent, default=str)

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Geography reference (Boreal Passage)
# ---------------------------------------------------------------------------

DEFENDED_ZONES = {
    "zone-arktholm": {"x_km": 250, "y_km": 400, "radius_km": 60, "priority": 1, "name": "Arktholm"},
    "zone-valbrek": {"x_km": 180, "y_km": 350, "radius_km": 40, "priority": 2, "name": "Valbrek"},
    "zone-meridia": {"x_km": 300, "y_km": 120, "radius_km": 50, "priority": 1, "name": "Meridia"},
    "zone-nordvik": {"x_km": 320, "y_km": 300, "radius_km": 35, "priority": 3, "name": "Nordvik"},
}

SENSORS = {
    "sensor-boreal": {"x_km": 150, "y_km": 480, "range_km": 250, "type": "long_range_radar"},
    "sensor-highridge": {"x_km": 310, "y_km": 430, "range_km": 200, "type": "medium_range_radar"},
    "sensor-spear": {"x_km": 360, "y_km": 210, "range_km": 180, "type": "medium_range_radar"},
}

BASES = {
    "base-north": {"x_km": 200, "y_km": 550},
    "base-highridge": {"x_km": 300, "y_km": 420},
    "base-south": {"x_km": 280, "y_km": 150},
    "base-spear": {"x_km": 350, "y_km": 200},
}

PROTECTED_ASSETS = [
    {"id": "asset-runway-north", "type": "runway", "base_id": "base-north", "x_km": 200, "y_km": 550},
    {"id": "asset-runway-highridge", "type": "runway", "base_id": "base-highridge", "x_km": 300, "y_km": 420},
    {"id": "asset-radar-boreal", "type": "radar", "base_id": None, "x_km": 150, "y_km": 480},
    {"id": "asset-fuel-highridge", "type": "fuel_depot", "base_id": "base-highridge", "x_km": 305, "y_km": 415},
    {"id": "asset-command-arktholm", "type": "command_post", "base_id": None, "x_km": 250, "y_km": 400},
    {"id": "asset-parking-north", "type": "aircraft_parking", "base_id": "base-north", "x_km": 195, "y_km": 548},
    {"id": "asset-sam-firewatch", "type": "sam_site", "base_id": None, "x_km": 220, "y_km": 370},
]


# ---------------------------------------------------------------------------
# Ingress corridor definitions
# ---------------------------------------------------------------------------

INGRESS_CORRIDORS = {
    "corridor-nw": {
        "name": "Northwest Approach",
        "entry_box": {"x_min": 50, "x_max": 180, "y_min": 570, "y_max": 600},
        "heading_range": (170, 210),
        "target_zones": ["zone-arktholm", "zone-valbrek"],
    },
    "corridor-n": {
        "name": "Northern Central",
        "entry_box": {"x_min": 180, "x_max": 320, "y_min": 580, "y_max": 600},
        "heading_range": (175, 200),
        "target_zones": ["zone-arktholm"],
    },
    "corridor-ne": {
        "name": "Northeast Approach",
        "entry_box": {"x_min": 320, "x_max": 400, "y_min": 560, "y_max": 600},
        "heading_range": (190, 230),
        "target_zones": ["zone-arktholm", "zone-nordvik"],
    },
    "corridor-e": {
        "name": "Eastern Flank",
        "entry_box": {"x_min": 380, "x_max": 400, "y_min": 350, "y_max": 550},
        "heading_range": (240, 280),
        "target_zones": ["zone-nordvik"],
    },
}


# ---------------------------------------------------------------------------
# Track generation helpers
# ---------------------------------------------------------------------------

class TrackFactory:
    """Generates individual tracks with configurable randomness."""

    def __init__(self, rng: random.Random):
        self.rng = rng
        self._track_counter = 0

    def _next_id(self, prefix: str = "trk-h") -> str:
        self._track_counter += 1
        return f"{prefix}{self._track_counter:02d}"

    def _pick_sensors(self, x: float, y: float) -> list:
        """Which sensors would detect a track at this position."""
        visible = []
        for sid, s in SENSORS.items():
            dist = math.sqrt((x - s["x_km"])**2 + (y - s["y_km"])**2)
            if dist <= s["range_km"]:
                visible.append(sid)
        return visible if visible else ["sensor-boreal"]  # fallback

    def _compute_path(self, x0: float, y0: float, heading: float,
                      speed_class: str, duration_s: int, t_start: int) -> list:
        """Simple linear path projection."""
        speeds = {"slow": 3.0, "medium": 7.0, "fast": 14.0}  # km per sim-second
        spd = speeds.get(speed_class, 7.0)
        rad = math.radians(heading)
        dx = math.sin(rad) * spd
        dy = -math.cos(rad) * spd  # heading 180 = south = -y
        path = []
        for dt in range(0, duration_s + 1, max(duration_s // 5, 10)):
            path.append({
                "t_s": t_start + dt,
                "x_km": round(x0 + dx * dt, 1),
                "y_km": round(y0 + dy * dt, 1),
            })
        return path

    def _nearest_zone(self, x: float, y: float, heading: float):
        """Find the defended zone most aligned with this track's heading."""
        best = None
        best_score = -1
        rad = math.radians(heading)
        dx_h = math.sin(rad)
        dy_h = -math.cos(rad)
        for zid, z in DEFENDED_ZONES.items():
            dx = z["x_km"] - x
            dy = z["y_km"] - y
            dist = math.sqrt(dx**2 + dy**2)
            if dist < 1:
                continue
            dot = (dx * dx_h + dy * dy_h) / dist
            score = dot * z["priority"] / max(dist, 1)
            if score > best_score:
                best_score = score
                best = zid
        return best

    def make_track(self, corridor_id: str, class_label: str,
                   speed_class: str, altitude_band: str,
                   confidence: float, t_start: int,
                   group_seed_id: str = None,
                   formation_hint: str = None,
                   decoy_prob: float = None,
                   payload_known: bool = True,
                   payload_type: str = None,
                   rf_emitting: bool = None,
                   source_disagreement: bool = False,
                   maneuver_pattern: str = "straight",
                   notes: str = "") -> tuple:
        """Create a track and its TRACK_CREATED event."""
        corridor = INGRESS_CORRIDORS[corridor_id]
        box = corridor["entry_box"]
        x = round(self.rng.uniform(box["x_min"], box["x_max"]), 1)
        y = round(self.rng.uniform(box["y_min"], box["y_max"]), 1)
        h_min, h_max = corridor["heading_range"]
        heading = round(self.rng.uniform(h_min, h_max), 1)

        # Add small jitter
        x += round(self.rng.gauss(0, 5), 1)
        y += round(self.rng.gauss(0, 3), 1)
        heading += round(self.rng.gauss(0, 3), 1)

        track_id = self._next_id()
        sensors = self._pick_sensors(x, y)

        # Degrade confidence if source disagreement
        if source_disagreement:
            confidence = round(max(0.3, confidence - self.rng.uniform(0.1, 0.25)), 2)

        path = self._compute_path(x, y, heading, speed_class, 180, t_start)

        # Signature hint based on class
        sig_hints = {
            TrackClass.FIGHTER.value: "jet_engine_signature",
            TrackClass.CRUISE.value: "small_turbofan_signature",
            TrackClass.UAV_RECON.value: "electric_motor_low_rcs",
            TrackClass.UAV_ARMED.value: "electric_motor_medium_rcs",
            TrackClass.UAV_SWARM.value: "swarm_rf_mesh",
            TrackClass.DECOY.value: "rf_emitter_no_propulsion_match",
            TrackClass.JAMMER.value: "strong_rf_emitter",
        }

        track = TrackEvent(
            track_id=track_id,
            side=Side.HOSTILE.value,
            class_label=class_label,
            confidence=confidence,
            x_km=x, y_km=y,
            heading_deg=round(heading, 1),
            speed_class=speed_class,
            altitude_band=altitude_band,
            detected_by=sensors,
            predicted_path=path,
            notes=notes,
            corridor_id=corridor_id,
            signature_hint=sig_hints.get(class_label, "unknown"),
            decoy_probability=decoy_prob,
            formation_hint=formation_hint,
            source_disagreement=source_disagreement,
            group_seed_id=group_seed_id,
            payload_known=payload_known,
            payload_type=payload_type,
            rf_emitting=rf_emitting,
            maneuver_pattern=maneuver_pattern,
        )

        event = ScenarioEvent(
            t_s=t_start,
            event_type=EventType.TRACK_CREATED.value,
            data=asdict(track),
        )

        return track, event


# ---------------------------------------------------------------------------
# Threat group templates
# ---------------------------------------------------------------------------

class ThreatGroupTemplate:
    """Defines how to generate a coherent threat group."""

    @staticmethod
    def drone_swarm(rng: random.Random, factory: TrackFactory,
                    corridor: str, t_start: int, size: int = None,
                    group_seed: str = None) -> list:
        """Generate a coordinated sUAS swarm."""
        if size is None:
            size = rng.randint(8, 24)
        if group_seed is None:
            group_seed = f"swarm-{uuid.uuid4().hex[:6]}"

        events = []
        for i in range(size):
            t = t_start + rng.randint(0, 8)  # tight temporal clustering
            payload_known = rng.random() > 0.3  # 30% payload unknown
            armed = rng.random() > 0.4
            _, ev = factory.make_track(
                corridor_id=corridor,
                class_label=TrackClass.UAV_ARMED.value if armed else TrackClass.UAV_RECON.value,
                speed_class=SpeedClass.SLOW.value,
                altitude_band=AltitudeBand.VERY_LOW.value,
                confidence=round(rng.uniform(0.45, 0.75), 2),
                t_start=t,
                group_seed_id=group_seed,
                formation_hint="swarm_mesh" if i < size - 2 else "trailing",
                decoy_prob=round(rng.uniform(0.0, 0.15), 2),
                payload_known=payload_known,
                payload_type="fpv_munition" if armed and payload_known else None,
                rf_emitting=True,
                maneuver_pattern="swarm_coordinated",
                notes=f"Swarm element {i+1}/{size}. Group seed: {group_seed}.",
            )
            events.append(ev)
        return events

    @staticmethod
    def mixed_raid(rng: random.Random, factory: TrackFactory,
                   corridors: list, t_start: int,
                   group_seed: str = None) -> list:
        """Generate a mixed raid: fighters + cruise + decoys across corridors."""
        if group_seed is None:
            group_seed = f"raid-{uuid.uuid4().hex[:6]}"

        events = []
        # Lead fighters
        for c in corridors[:2]:
            _, ev = factory.make_track(
                corridor_id=c,
                class_label=TrackClass.FIGHTER.value,
                speed_class=SpeedClass.FAST.value,
                altitude_band=rng.choice([AltitudeBand.MEDIUM.value, AltitudeBand.HIGH.value]),
                confidence=round(rng.uniform(0.70, 0.90), 2),
                t_start=t_start + rng.randint(0, 5),
                group_seed_id=group_seed,
                formation_hint="strike_lead",
                payload_known=True,
                payload_type="air_to_ground",
                rf_emitting=False,
                maneuver_pattern="direct_ingress",
                notes=f"Raid lead element. Group: {group_seed}.",
            )
            events.append(ev)

        # Cruise missiles
        n_cruise = rng.randint(2, 4)
        for i in range(n_cruise):
            c = rng.choice(corridors)
            _, ev = factory.make_track(
                corridor_id=c,
                class_label=TrackClass.CRUISE.value,
                speed_class=SpeedClass.MEDIUM.value,
                altitude_band=AltitudeBand.VERY_LOW.value,
                confidence=round(rng.uniform(0.60, 0.80), 2),
                t_start=t_start + rng.randint(5, 15),
                group_seed_id=group_seed,
                formation_hint="independent_track",
                decoy_prob=round(rng.uniform(0.0, 0.1), 2),
                payload_known=rng.random() > 0.5,
                rf_emitting=False,
                maneuver_pattern="terrain_following",
                notes=f"Cruise element {i+1}. Group: {group_seed}.",
            )
            events.append(ev)

        # Decoys
        n_decoys = rng.randint(1, 3)
        for i in range(n_decoys):
            c = rng.choice(corridors)
            _, ev = factory.make_track(
                corridor_id=c,
                class_label=TrackClass.DECOY.value,
                speed_class=SpeedClass.SLOW.value,
                altitude_band=AltitudeBand.MEDIUM.value,
                confidence=round(rng.uniform(0.30, 0.55), 2),
                t_start=t_start + rng.randint(0, 10),
                group_seed_id=group_seed,
                formation_hint="dispersed",
                decoy_prob=round(rng.uniform(0.5, 0.9), 2),
                payload_known=False,
                rf_emitting=True,  # decoys emit to attract attention
                source_disagreement=rng.random() > 0.5,
                maneuver_pattern="erratic",
                notes=f"Suspected decoy {i+1}. Group: {group_seed}.",
            )
            events.append(ev)

        return events

    @staticmethod
    def recon_probe(rng: random.Random, factory: TrackFactory,
                    corridor: str, t_start: int,
                    group_seed: str = None) -> list:
        """Generate a small recon probe — 1-3 slow UAVs."""
        if group_seed is None:
            group_seed = f"probe-{uuid.uuid4().hex[:6]}"

        events = []
        n = rng.randint(1, 3)
        for i in range(n):
            _, ev = factory.make_track(
                corridor_id=corridor,
                class_label=TrackClass.UAV_RECON.value,
                speed_class=SpeedClass.SLOW.value,
                altitude_band=rng.choice([AltitudeBand.LOW.value, AltitudeBand.VERY_LOW.value]),
                confidence=round(rng.uniform(0.40, 0.65), 2),
                t_start=t_start + rng.randint(0, 12),
                group_seed_id=group_seed,
                formation_hint="loose_spread",
                decoy_prob=round(rng.uniform(0.1, 0.4), 2),
                payload_known=False,
                rf_emitting=rng.random() > 0.5,
                source_disagreement=rng.random() > 0.7,
                maneuver_pattern="loiter_advance",
                notes=f"Recon probe element {i+1}. Group: {group_seed}.",
            )
            events.append(ev)
        return events

    @staticmethod
    def ew_screen(rng: random.Random, factory: TrackFactory,
                  corridor: str, t_start: int,
                  group_seed: str = None) -> list:
        """Generate an electronic warfare screen — jammer + decoys."""
        if group_seed is None:
            group_seed = f"ew-{uuid.uuid4().hex[:6]}"

        events = []
        # Jammer
        _, ev = factory.make_track(
            corridor_id=corridor,
            class_label=TrackClass.JAMMER.value,
            speed_class=SpeedClass.MEDIUM.value,
            altitude_band=AltitudeBand.MEDIUM.value,
            confidence=round(rng.uniform(0.50, 0.70), 2),
            t_start=t_start,
            group_seed_id=group_seed,
            formation_hint="standoff",
            rf_emitting=True,
            maneuver_pattern="orbit",
            notes=f"EW jammer platform. Group: {group_seed}.",
        )
        events.append(ev)

        # Escort decoys
        for i in range(rng.randint(1, 2)):
            _, ev = factory.make_track(
                corridor_id=corridor,
                class_label=TrackClass.DECOY.value,
                speed_class=SpeedClass.SLOW.value,
                altitude_band=AltitudeBand.LOW.value,
                confidence=round(rng.uniform(0.25, 0.50), 2),
                t_start=t_start + rng.randint(2, 8),
                group_seed_id=group_seed,
                formation_hint="ew_escort",
                decoy_prob=round(rng.uniform(0.6, 0.9), 2),
                rf_emitting=True,
                source_disagreement=True,
                maneuver_pattern="erratic",
                notes=f"EW escort decoy {i+1}. Group: {group_seed}.",
            )
            events.append(ev)
        return events


# ---------------------------------------------------------------------------
# Dynamic event injector
# ---------------------------------------------------------------------------

class DynamicInjector:
    """
    Generates runtime perturbations that can be injected into a running scenario.
    Call these methods during scenario playback to mutate the situation.
    """

    def __init__(self, rng: random.Random):
        self.rng = rng

    def sensor_degradation(self, t_s: int, sensor_id: str, severity: str = "partial") -> ScenarioEvent:
        return ScenarioEvent(
            t_s=t_s,
            event_type=EventType.SENSOR_DEGRADED.value,
            data={
                "sensor_id": sensor_id,
                "severity": severity,  # partial | full | intermittent
                "detection_range_multiplier": round(self.rng.uniform(0.3, 0.7), 2) if severity == "partial" else 0.0,
                "reason": self.rng.choice(["electronic_attack", "hardware_fault", "weather_attenuation"]),
                "estimated_recovery_s": self.rng.randint(30, 120) if severity != "full" else None,
                "notes": f"Sensor {sensor_id} degraded — {severity}.",
            },
        )

    def asset_readiness_change(self, t_s: int, asset_id: str,
                                new_readiness: float, reason: str) -> ScenarioEvent:
        return ScenarioEvent(
            t_s=t_s,
            event_type=EventType.CONSTRAINT_CHANGED.value,
            data={
                "constraint_type": "asset_readiness_degraded",
                "asset_id": asset_id,
                "new_readiness": new_readiness,
                "reason": reason,
                "notes": f"Asset {asset_id} readiness changed to {new_readiness}: {reason}.",
            },
        )

    def base_status_change(self, t_s: int, base_id: str,
                            new_status: str, reason: str) -> ScenarioEvent:
        return ScenarioEvent(
            t_s=t_s,
            event_type=EventType.CONSTRAINT_CHANGED.value,
            data={
                "constraint_type": "base_status_changed",
                "base_id": base_id,
                "new_status": new_status,  # operational | degraded | closed
                "reason": reason,
                "notes": f"Base {base_id} status changed to {new_status}: {reason}.",
            },
        )

    def track_reclassification(self, t_s: int, track_id: str,
                                new_class: str, new_confidence: float,
                                reason: str) -> ScenarioEvent:
        return ScenarioEvent(
            t_s=t_s,
            event_type=EventType.TRACK_UPDATED.value,
            data={
                "track_id": track_id,
                "updates": {
                    "class_label": new_class,
                    "confidence": new_confidence,
                },
                "reclassification_reason": reason,
                "notes": f"Track {track_id} reclassified to {new_class} (conf: {new_confidence}): {reason}.",
            },
        )

    def random_perturbation(self, t_s: int) -> ScenarioEvent:
        """Generate a random but plausible perturbation."""
        choice = self.rng.choice(["sensor", "asset", "base"])
        if choice == "sensor":
            sid = self.rng.choice(list(SENSORS.keys()))
            return self.sensor_degradation(t_s, sid, self.rng.choice(["partial", "intermittent"]))
        elif choice == "asset":
            return self.asset_readiness_change(
                t_s,
                self.rng.choice(["ftr-n3", "ftr-h2", "uav-h1", "sam-fw"]),
                round(self.rng.uniform(0.3, 0.65), 2),
                self.rng.choice(["maintenance_issue", "battle_damage", "crew_unavailable"]),
            )
        else:
            bid = self.rng.choice(list(BASES.keys()))
            return self.base_status_change(
                t_s, bid, "degraded",
                self.rng.choice(["runway_damage", "fuel_contamination", "comms_fault"]),
            )


# ---------------------------------------------------------------------------
# Scenario generator
# ---------------------------------------------------------------------------

SCENARIO_TEMPLATES = {
    "swarm_pressure": {
        "name": "Drone Swarm Pressure Test",
        "description": "Coordinated sUAS swarm targeting base infrastructure, preceded by recon probe and accompanied by EW screen. Tests group-level reasoning, decoy discrimination, cost-aware response ranking, and human decision card under time pressure.",
        "duration_s": 300,
        "phases": [
            {"t_s": 0, "type": "scenario_start"},
            {"t_s": 10, "type": "recon_probe", "corridor": "corridor-nw"},
            {"t_s": 40, "type": "ew_screen", "corridor": "corridor-n"},
            {"t_s": 60, "type": "drone_swarm", "corridor": "corridor-n", "size_range": [12, 20]},
            {"t_s": 65, "type": "drone_swarm", "corridor": "corridor-ne", "size_range": [6, 12]},
            {"t_s": 120, "type": "perturbation"},
            {"t_s": 150, "type": "mixed_raid", "corridors": ["corridor-nw", "corridor-n"]},
            {"t_s": 200, "type": "perturbation"},
            {"t_s": 300, "type": "scenario_end"},
        ],
    },
    "multi_axis_raid": {
        "name": "Multi-Axis Coordinated Raid",
        "description": "Three-corridor mixed raid with fighters, cruise missiles, and decoys. Tests multi-axis threat grouping and resource scarcity under simultaneous attack.",
        "duration_s": 240,
        "phases": [
            {"t_s": 0, "type": "scenario_start"},
            {"t_s": 10, "type": "mixed_raid", "corridors": ["corridor-nw", "corridor-n", "corridor-ne"]},
            {"t_s": 80, "type": "perturbation"},
            {"t_s": 100, "type": "drone_swarm", "corridor": "corridor-e", "size_range": [8, 16]},
            {"t_s": 160, "type": "perturbation"},
            {"t_s": 240, "type": "scenario_end"},
        ],
    },
    "escalating_probe": {
        "name": "Escalating Probe to Full Attack",
        "description": "Starts with ambiguous recon tracks, escalates through EW activity to full swarm. Tests slow-lane-to-fast-lane transition and progressive confidence building.",
        "duration_s": 360,
        "phases": [
            {"t_s": 0, "type": "scenario_start"},
            {"t_s": 15, "type": "recon_probe", "corridor": "corridor-nw"},
            {"t_s": 45, "type": "recon_probe", "corridor": "corridor-ne"},
            {"t_s": 90, "type": "ew_screen", "corridor": "corridor-n"},
            {"t_s": 130, "type": "perturbation"},
            {"t_s": 150, "type": "drone_swarm", "corridor": "corridor-n", "size_range": [16, 24]},
            {"t_s": 220, "type": "mixed_raid", "corridors": ["corridor-nw", "corridor-ne"]},
            {"t_s": 280, "type": "perturbation"},
            {"t_s": 360, "type": "scenario_end"},
        ],
    },
}


class ScenarioGenerator:
    """
    Generate complete scenarios from templates with controllable randomness.

    Usage:
        gen = ScenarioGenerator(seed=42)
        scenario = gen.generate("swarm_pressure")
        scenario.to_json("scenario_swarm_beta.json")

        # Or generate a fully random scenario:
        scenario = gen.generate_random()
    """

    def __init__(self, seed: int = None):
        self.seed = seed if seed is not None else random.randint(0, 2**32)
        self.rng = random.Random(self.seed)
        self.factory = TrackFactory(self.rng)
        self.injector = DynamicInjector(self.rng)

    def generate(self, template: str = "swarm_pressure") -> Scenario:
        """Generate a scenario from a named template."""
        tmpl = SCENARIO_TEMPLATES[template]
        events = []

        for phase in tmpl["phases"]:
            t = phase["t_s"]
            ptype = phase["type"]

            if ptype == "scenario_start":
                events.append(ScenarioEvent(t, EventType.SCENARIO_START.value, {
                    "message": f"Scenario initiated: {tmpl['name']}. Seed: {self.seed}.",
                    "posture": "peacetime",
                }))

            elif ptype == "recon_probe":
                group_events = ThreatGroupTemplate.recon_probe(
                    self.rng, self.factory, phase["corridor"], t)
                events.extend(group_events)
                events.append(ScenarioEvent(
                    t + 2, EventType.GROUP_FORMED.value, {
                        "group_type": ThreatGroupType.RECON_OR_DECOY_SCREEN.value,
                        "corridor": phase["corridor"],
                        "track_count": len(group_events),
                        "recommended_lane": WorkflowLane.SLOW.value,
                        "notes": "Recon probe detected. Low confidence. Slow lane.",
                    }))

            elif ptype == "ew_screen":
                group_events = ThreatGroupTemplate.ew_screen(
                    self.rng, self.factory, phase["corridor"], t)
                events.extend(group_events)
                events.append(ScenarioEvent(
                    t + 3, EventType.GROUP_FORMED.value, {
                        "group_type": ThreatGroupType.RECON_OR_DECOY_SCREEN.value,
                        "corridor": phase["corridor"],
                        "track_count": len(group_events),
                        "recommended_lane": WorkflowLane.SLOW.value,
                        "notes": "EW screen activity detected. Possible precursor to main attack.",
                    }))

            elif ptype == "drone_swarm":
                lo, hi = phase.get("size_range", [10, 20])
                size = self.rng.randint(lo, hi)
                group_events = ThreatGroupTemplate.drone_swarm(
                    self.rng, self.factory, phase["corridor"], t, size=size)
                events.extend(group_events)
                events.append(ScenarioEvent(
                    t + 5, EventType.GROUP_FORMED.value, {
                        "group_type": ThreatGroupType.PROBABLE_SWARM.value,
                        "corridor": phase["corridor"],
                        "track_count": len(group_events),
                        "recommended_lane": WorkflowLane.FAST.value,
                        "notes": f"Probable coordinated sUAS swarm. {size} tracks. Fast lane.",
                    }))

            elif ptype == "mixed_raid":
                group_events = ThreatGroupTemplate.mixed_raid(
                    self.rng, self.factory, phase["corridors"], t)
                events.extend(group_events)
                events.append(ScenarioEvent(
                    t + 5, EventType.GROUP_FORMED.value, {
                        "group_type": ThreatGroupType.MIXED_RAID_WITH_DECOYS.value,
                        "corridors": phase["corridors"],
                        "track_count": len(group_events),
                        "recommended_lane": WorkflowLane.FAST.value,
                        "notes": f"Mixed raid detected across {len(phase['corridors'])} corridors. Includes probable decoys.",
                    }))

            elif ptype == "perturbation":
                events.append(self.injector.random_perturbation(t))

            elif ptype == "scenario_end":
                events.append(ScenarioEvent(t, EventType.SCENARIO_END.value, {
                    "message": f"Scenario complete. Seed: {self.seed}.",
                    "scoring_notes": "Evaluate: threats grouped, discrimination accuracy, response cost-effectiveness, decision speed, reserve preservation.",
                }))

        # Sort events by time, stable
        events.sort(key=lambda e: e.t_s)

        return Scenario(
            meta={
                "scenario_id": f"scenario-gen-{self.seed}",
                "name": tmpl["name"],
                "description": tmpl["description"],
                "version": "2.0",
                "duration_s": tmpl["duration_s"],
                "seed": self.seed,
                "template": template,
                "generator": "neon_command_scenario_generator_v1",
                "total_events": len(events),
                "group_aware": True,
                "extended_fields": [
                    "corridor_id", "signature_hint", "decoy_probability",
                    "formation_hint", "source_disagreement", "group_seed_id",
                    "payload_known", "payload_type", "rf_emitting", "maneuver_pattern",
                ],
            },
            initial_state={
                "posture": "peacetime",
                "alert_level": "normal",
                "notes": "All assets at baseline readiness. Sensors nominal.",
            },
            events=[asdict(e) for e in events],
        )

    def generate_random(self, duration_s: int = 300) -> Scenario:
        """Generate a fully randomized scenario — no template."""
        events = []
        events.append(ScenarioEvent(0, EventType.SCENARIO_START.value, {
            "message": f"Random scenario. Seed: {self.seed}.",
            "posture": "peacetime",
        }))

        t = 10
        while t < duration_s - 30:
            group_type = self.rng.choice(["swarm", "raid", "probe", "ew"])
            corridor = self.rng.choice(list(INGRESS_CORRIDORS.keys()))

            if group_type == "swarm":
                size = self.rng.randint(6, 24)
                evts = ThreatGroupTemplate.drone_swarm(
                    self.rng, self.factory, corridor, t, size=size)
                events.extend(evts)
                events.append(ScenarioEvent(t + 5, EventType.GROUP_FORMED.value, {
                    "group_type": ThreatGroupType.PROBABLE_SWARM.value,
                    "corridor": corridor, "track_count": len(evts),
                    "recommended_lane": WorkflowLane.FAST.value,
                }))
                t += self.rng.randint(40, 80)

            elif group_type == "raid":
                n_corridors = self.rng.randint(1, 3)
                corrs = self.rng.sample(list(INGRESS_CORRIDORS.keys()), n_corridors)
                evts = ThreatGroupTemplate.mixed_raid(
                    self.rng, self.factory, corrs, t)
                events.extend(evts)
                events.append(ScenarioEvent(t + 5, EventType.GROUP_FORMED.value, {
                    "group_type": ThreatGroupType.MIXED_RAID_WITH_DECOYS.value,
                    "corridors": corrs, "track_count": len(evts),
                    "recommended_lane": WorkflowLane.FAST.value,
                }))
                t += self.rng.randint(50, 100)

            elif group_type == "probe":
                evts = ThreatGroupTemplate.recon_probe(
                    self.rng, self.factory, corridor, t)
                events.extend(evts)
                events.append(ScenarioEvent(t + 2, EventType.GROUP_FORMED.value, {
                    "group_type": ThreatGroupType.RECON_OR_DECOY_SCREEN.value,
                    "corridor": corridor, "track_count": len(evts),
                    "recommended_lane": WorkflowLane.SLOW.value,
                }))
                t += self.rng.randint(20, 50)

            elif group_type == "ew":
                evts = ThreatGroupTemplate.ew_screen(
                    self.rng, self.factory, corridor, t)
                events.extend(evts)
                events.append(ScenarioEvent(t + 3, EventType.GROUP_FORMED.value, {
                    "group_type": ThreatGroupType.RECON_OR_DECOY_SCREEN.value,
                    "corridor": corridor, "track_count": len(evts),
                    "recommended_lane": WorkflowLane.SLOW.value,
                }))
                t += self.rng.randint(30, 60)

            # Random perturbation sometimes
            if self.rng.random() > 0.6:
                events.append(self.injector.random_perturbation(t - 5))

        events.append(ScenarioEvent(duration_s, EventType.SCENARIO_END.value, {
            "message": f"Random scenario complete. Seed: {self.seed}.",
        }))

        events.sort(key=lambda e: e.t_s if isinstance(e, ScenarioEvent) else e["t_s"])

        return Scenario(
            meta={
                "scenario_id": f"scenario-random-{self.seed}",
                "name": "Randomized Scenario",
                "description": "Fully randomized threat scenario for stress testing.",
                "version": "2.0",
                "duration_s": duration_s,
                "seed": self.seed,
                "template": "random",
                "generator": "neon_command_scenario_generator_v1",
                "total_events": len(events),
                "group_aware": True,
            },
            initial_state={"posture": "peacetime", "alert_level": "normal"},
            events=[asdict(e) if isinstance(e, ScenarioEvent) else e for e in events],
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LJFC COMMAND Scenario Generator")
    parser.add_argument("--template", default="swarm_pressure",
                        choices=list(SCENARIO_TEMPLATES.keys()) + ["random"],
                        help="Scenario template to use")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--output", default=None,
                        help="Output JSON file path")
    parser.add_argument("--duration", type=int, default=300,
                        help="Duration in seconds (random template only)")
    args = parser.parse_args()

    gen = ScenarioGenerator(seed=args.seed)

    if args.template == "random":
        scenario = gen.generate_random(duration_s=args.duration)
    else:
        scenario = gen.generate(args.template)

    output = args.output or f"scenario_{args.template}_{gen.seed}.json"
    scenario.to_json(output)

    print(f"Generated: {output}")
    print(f"  Template: {args.template}")
    print(f"  Seed: {gen.seed}")
    print(f"  Events: {len(scenario.events)}")
    print(f"  Duration: {scenario.meta['duration_s']}s")
