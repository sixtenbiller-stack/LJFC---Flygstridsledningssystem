"""
Scenario Runtime — bridges generator/mutator into the NEON COMMAND backend.

Provides:
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

from scenario_mutator import ScenarioMutator  # noqa: E402

from scenario_registry import RUNTIME_DIR, load_scenario_raw  # noqa: E402

AVAILABLE_TEMPLATES = ["random"]


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
        """Perform a live injection (not implemented - scenario generator removed)."""
        return {"error": "Injections disabled - Scenario Generator removed."}

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
