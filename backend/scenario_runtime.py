"""
Scenario Runtime — bridges generator/mutator into the NEON COMMAND backend.

Provides:
  - generate_scenario(): create scenario from template + seed, save to generated/
  - LiveSession: wraps ScenarioMutator for live-mode operation
"""
from __future__ import annotations

import json
import sys
import time
import copy
from pathlib import Path
from typing import Any

ENGINE_DIR = Path(__file__).resolve().parent.parent / "neon-command-engine"
sys.path.insert(0, str(ENGINE_DIR))

from scenario_generator import ScenarioGenerator, SCENARIO_TEMPLATES  # noqa: E402
from scenario_mutator import ScenarioMutator  # noqa: E402

from scenario_registry import GENERATED_DIR, RUNTIME_DIR, load_scenario_raw  # noqa: E402

AVAILABLE_TEMPLATES = list(SCENARIO_TEMPLATES.keys()) + ["random"]


def generate_scenario(
    template: str = "swarm_pressure",
    seed: int | None = None,
    duration_s: int = 300,
    output_name: str | None = None,
) -> dict[str, Any]:
    """Generate a scenario and write to generated/ dir. Returns metadata."""
    gen = ScenarioGenerator(seed=seed)

    if template == "random":
        scenario = gen.generate_random(duration_s=duration_s)
    else:
        scenario = gen.generate(template)

    data = scenario.to_dict()
    file_id = output_name or f"scenario_{template}_{gen.seed}"
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = GENERATED_DIR / f"{file_id}.json"
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return {
        "file_id": file_id,
        "path": str(out_path),
        "seed": gen.seed,
        "template": template,
        "duration_s": data["meta"].get("duration_s", duration_s),
        "total_events": len(data["events"]),
    }


class LiveSession:
    """Wraps ScenarioMutator for API-driven live-mode operation."""

    def __init__(self, file_id: str, seed: int | None = None):
        raw = load_scenario_raw(file_id)
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        session_tag = str(int(time.time()))
        self._runtime_path = RUNTIME_DIR / f"{file_id}_{session_tag}.json"
        with open(self._runtime_path, "w") as f:
            json.dump(raw, f, indent=2, default=str)

        self.file_id = file_id
        self.session_id = f"live-{file_id}-{session_tag}"
        self._mutator = ScenarioMutator(str(self._runtime_path), seed=seed)
        self._playing = False
        self._speed = 1.0
        self._last_wall = time.monotonic()
        self._injection_log: list[dict] = []

    @property
    def current_time_s(self) -> int:
        return self._mutator.state.current_t_s

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        self._playing = True
        self._last_wall = time.monotonic()

    def pause(self) -> None:
        self._playing = False

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.5, min(speed, 8.0))

    def reset(self) -> None:
        raw = load_scenario_raw(self.file_id)
        with open(self._runtime_path, "w") as f:
            json.dump(raw, f, indent=2, default=str)
        self._mutator = ScenarioMutator(str(self._runtime_path))
        self._playing = False
        self._injection_log = []

    def tick(self, dt_s: int | None = None) -> None:
        """Advance time. If dt_s is None, use wall-clock elapsed."""
        if dt_s is None:
            now = time.monotonic()
            elapsed = now - self._last_wall
            self._last_wall = now
            dt_s = max(1, int(elapsed * self._speed))
        self._mutator.tick(dt_s=dt_s)

    def inject(self, inject_type: str, params: dict | None = None) -> dict:
        """Perform a live injection (swarm, raid, sensor_degrade, etc)."""
        params = params or {}
        t = self._mutator.state.current_t_s + 1
        result: dict[str, Any] = {"type": inject_type, "t_s": t}

        if inject_type == "swarm":
            corridor = params.get("corridor", "corridor-n")
            size = params.get("size", 12)
            events = self._mutator.inject_swarm(t_s=t, corridor=corridor, size=size)
            result["events_added"] = len(events)
        elif inject_type == "second_wave":
            corridors = params.get("corridors", ["corridor-nw", "corridor-n"])
            events = self._mutator.inject_raid(t_s=t, corridors=corridors)
            result["events_added"] = len(events)
        elif inject_type == "sensor_degrade":
            sensor_id = params.get("sensor_id", "sensor-boreal")
            severity = params.get("severity", "partial")
            event = self._mutator.degrade_sensor(t_s=t, sensor_id=sensor_id, severity=severity)
            result["event"] = event
        elif inject_type == "reclassify":
            track_id = params.get("track_id", "")
            new_class = params.get("new_class", "decoy-suspected")
            new_conf = params.get("new_confidence", 0.3)
            reason = params.get("reason", "Operator reclassification")
            event = self._mutator.reclassify_track(t_s=t, track_id=track_id,
                                                   new_class=new_class,
                                                   new_confidence=new_conf,
                                                   reason=reason)
            result["event"] = event
        elif inject_type == "readiness_drop":
            result["note"] = "Readiness reduction applied via CONSTRAINT_CHANGED"
            event = self._mutator.inject_perturbation(t_s=t)
            result["event"] = event
        else:
            result["error"] = f"Unknown inject type: {inject_type}"

        self._injection_log.append(result)
        return result

    def get_state_snapshot(self) -> dict[str, Any]:
        """Return normalized snapshot for frontend consumption."""
        snap = self._mutator.export_live_state()
        snap["session_id"] = self.session_id
        snap["file_id"] = self.file_id
        snap["mode"] = "live"
        snap["is_playing"] = self._playing
        snap["speed_multiplier"] = self._speed
        snap["injection_log"] = self._injection_log[-20:]
        return snap

    def get_events_for_engine(self) -> list[dict]:
        """Return all scenario events for loading into ScenarioEngine."""
        return list(self._mutator.scenario_data["events"])

    def get_meta(self) -> dict:
        return dict(self._mutator.scenario_data.get("meta", {}))
