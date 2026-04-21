"""
NEON COMMAND — Runtime Scenario Mutator
========================================
Provides dynamic mutation of scenario JSON files during system operation.

The design principle: JSON files remain the canonical data format that the
system reads. This module sits between the static scenario and the running
system, mutating the JSON at runtime to simulate a living, evolving
battlespace.

Three operating modes:
1. PRE-GENERATE: Generate a complete scenario with randomness, save to JSON,
   replay it deterministically. (What scenario_generator.py does.)
2. LIVE INJECT: While the scenario engine plays back, inject new events into
   the event stream. The mutator appends to the JSON file or provides events
   via an API endpoint.
3. CONTINUOUS EVOLVE: Run as a background process that periodically mutates
   track positions, degrades sensors, spawns new threats, and updates the
   JSON state file that the frontend polls.

Usage:
    from scenario_mutator import ScenarioMutator

    # Mode 2: inject a new swarm mid-scenario
    mutator = ScenarioMutator("scenario_swarm_beta.json", seed=42)
    new_events = mutator.inject_swarm(t_s=180, corridor="corridor-ne", size=8)
    mutator.save()

    # Mode 3: evolve all tracks by one timestep
    mutator.tick(dt_s=5)
    mutator.save()
"""

import json
import math
import random
import copy
from pathlib import Path
from typing import Optional
from dataclasses import asdict

# Mocked constants previously in scenario_generator.py
INGRESS_CORRIDORS = ["corridor-n", "corridor-ne", "corridor-nw", "corridor-e", "corridor-w"]
SENSORS = {}
DEFENDED_ZONES = {}

class ScenarioMutator:
    """
    Maintains the current state of all tracks and assets for runtime mutation.
    This is the in-memory representation that gets serialized back to JSON.
    """

    def __init__(self):
        self.tracks: dict = {}          # track_id -> track data dict
        self.groups: dict = {}          # group_seed_id -> group metadata
        self.alerts: list = []
        self.constraints: list = []
        self.sensor_states: dict = {}   # sensor_id -> state
        self.current_t_s: int = 0
        self.decisions: list = []

    def ingest_event(self, event: dict):
        """Process a scenario event and update live state."""
        etype = event["event_type"]
        data = event["data"]
        t = event["t_s"]
        self.current_t_s = max(self.current_t_s, t)

        if etype == "TRACK_CREATED":
            self.tracks[data["track_id"]] = {
                **data,
                "last_update_t_s": t,
                "status": "active",
            }
            # Register group membership
            gsid = data.get("group_seed_id")
            if gsid:
                if gsid not in self.groups:
                    self.groups[gsid] = {
                        "group_seed_id": gsid,
                        "member_track_ids": [],
                        "first_seen_t_s": t,
                    }
                self.groups[gsid]["member_track_ids"].append(data["track_id"])

        elif etype == "TRACK_UPDATED":
            tid = data.get("track_id")
            if tid and tid in self.tracks:
                updates = data.get("updates", {})
                self.tracks[tid].update(updates)
                self.tracks[tid]["last_update_t_s"] = t

        elif etype == "TRACK_LOST":
            tid = data.get("track_id")
            if tid and tid in self.tracks:
                self.tracks[tid]["status"] = "lost"
                self.tracks[tid]["last_update_t_s"] = t

        elif etype == "ALERT_CREATED":
            self.alerts.append({**data, "t_s": t})

        elif etype == "SENSOR_DEGRADED":
            sid = data.get("sensor_id")
            if sid:
                self.sensor_states[sid] = {
                    "status": data.get("severity", "degraded"),
                    "range_multiplier": data.get("detection_range_multiplier", 0.5),
                    "since_t_s": t,
                }

        elif etype == "CONSTRAINT_CHANGED":
            self.constraints.append({**data, "t_s": t})

        elif etype == "GROUP_FORMED":
            pass  # groups are tracked via group_seed_id on tracks

    def get_active_tracks(self) -> list:
        return [t for t in self.tracks.values() if t.get("status") == "active"]

    def get_group_tracks(self, group_seed_id: str) -> list:
        return [t for t in self.tracks.values()
                if t.get("group_seed_id") == group_seed_id and t.get("status") == "active"]

    def to_state_snapshot(self) -> dict:
        """Export current state as a JSON-serializable snapshot."""
        return {
            "timestamp_s": self.current_t_s,
            "active_tracks": self.get_active_tracks(),
            "groups": dict(self.groups),
            "active_alerts": self.alerts[-20:],  # last 20
            "sensor_states": dict(self.sensor_states),
            "constraints": self.constraints,
            "decisions": self.decisions,
        }


class ScenarioMutator:
    """
    Mutates a scenario JSON file at runtime.
    """

    def __init__(self, scenario_path: str, seed: int = None):
        self.path = Path(scenario_path)
        with open(self.path) as f:
            self.scenario_data = json.load(f)

        self.seed = seed if seed is not None else random.randint(0, 2**32)
        self.rng = random.Random(self.seed)
        self.state = LiveState()

        # Ingest all existing events up to current time
        for event in self.scenario_data["events"]:
            self.state.ingest_event(event)

    def _append_event(self, event: dict):
        """Append an event to the scenario data and update live state."""
        self.scenario_data["events"].append(event)
        self.state.ingest_event(event)

    # ----- Evolution methods -----

    def tick(self, dt_s: int = 5):
        """
        Advance all active tracks by dt_s seconds along their headings.
        This is the core "dynamic JSON update" — tracks move, the state evolves.
        """
        speeds = {"slow": 3.0, "medium": 7.0, "fast": 14.0}
        new_t = self.state.current_t_s + dt_s

        for tid, track in self.state.tracks.items():
            if track.get("status") != "active":
                continue

            spd = speeds.get(track.get("speed_class", "medium"), 7.0)
            heading = track.get("heading_deg", 180)
            rad = math.radians(heading)

            # Add slight random drift for realism
            drift_x = self.rng.gauss(0, 0.5)
            drift_y = self.rng.gauss(0, 0.5)

            new_x = track["x_km"] + math.sin(rad) * spd * dt_s + drift_x
            new_y = track["y_km"] - math.cos(rad) * spd * dt_s + drift_y

            # Clamp to bounds
            new_x = max(0, min(400, new_x))
            new_y = max(0, min(600, new_y))

            # Update track in state
            update_event = {
                "t_s": new_t,
                "event_type": "TRACK_UPDATED",
                "data": {
                    "track_id": tid,
                    "updates": {
                        "x_km": round(new_x, 1),
                        "y_km": round(new_y, 1),
                    },
                    "notes": f"Position update at t={new_t}s.",
                },
            }
            self._append_event(update_event)

        self.state.current_t_s = new_t

    # ----- Persistence -----

    def save(self, path: str = None):
        """Write the mutated scenario back to JSON."""
        out = path or str(self.path)
        # Re-sort events by time
        self.scenario_data["events"].sort(key=lambda e: e["t_s"])
        self.scenario_data["meta"]["total_events"] = len(self.scenario_data["events"])
        self.scenario_data["meta"]["mutated"] = True
        self.scenario_data["meta"]["mutation_seed"] = self.seed
        with open(out, "w") as f:
            json.dump(self.scenario_data, f, indent=2, default=str)

    def export_live_state(self, path: str = None) -> dict:
        """
        Export the current live state as a separate JSON file.
        This is what the frontend can poll for the current situation.
        """
        snapshot = self.state.to_state_snapshot()
        if path:
            with open(path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
        return snapshot


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEON COMMAND Scenario Mutator")
    parser.add_argument("scenario", help="Path to scenario JSON file")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--tick", type=int, default=0,
                        help="Advance all tracks by N seconds")
    parser.add_argument("--export-state", default=None,
                        help="Export live state to this path")
    parser.add_argument("--output", default=None,
                        help="Save mutated scenario to this path (default: overwrite)")
    args = parser.parse_args()

    mut = ScenarioMutator(args.scenario, seed=args.seed)
    print(f"Loaded: {args.scenario}")
    print(f"  Current time: {mut.state.current_t_s}s")
    print(f"  Active tracks: {len(mut.state.get_active_tracks())}")
    print(f"  Groups: {len(mut.state.groups)}")

    if args.tick > 0:
        mut.tick(dt_s=args.tick)
        print(f"  Ticked {args.tick}s → t={mut.state.current_t_s}s")
        print(f"  Active tracks: {len(mut.state.get_active_tracks())}")

    if args.export_state:
        mut.export_live_state(args.export_state)
        print(f"  Exported live state to: {args.export_state}")

    out = args.output or args.scenario
    mut.save(out)
    print(f"  Saved to: {out}")
    print(f"  Total events: {len(mut.scenario_data['events'])}")
