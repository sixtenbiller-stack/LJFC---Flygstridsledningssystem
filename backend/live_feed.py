"""Synthetic live-feed adapter for the minimal NEON COMMAND path.

The feed layer is intentionally thin: it loads JSONL feed events and presents
them through the existing scenario engine so map, scoring, grouping, COA,
simulation, approval, and audit flows keep working.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent.parent / "neon-command-data"
DEFAULT_FEED_ID = "live_feed_minimal_alpha"


@dataclass
class FeedEvent:
    feed_time_s: float
    event_id: str
    event_type: str
    source: str
    data: dict[str, Any]

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "FeedEvent":
        required = {"feed_time_s", "event_id", "event_type", "source", "data"}
        missing = required - set(raw)
        if missing:
            raise ValueError(f"Feed event missing required keys: {sorted(missing)}")
        if not isinstance(raw["data"], dict):
            raise ValueError(f"Feed event {raw.get('event_id', '?')} data must be an object")
        return cls(
            feed_time_s=float(raw["feed_time_s"]),
            event_id=str(raw["event_id"]),
            event_type=str(raw["event_type"]),
            source=str(raw["source"]),
            data=raw["data"],
        )

    def to_engine_event(self) -> dict[str, Any]:
        return {
            "t_s": self.feed_time_s,
            "event_type": self.event_type,
            "data": {
                **self.data,
                "feed_event_id": self.event_id,
                "feed_source": self.source,
                "message": self.data.get("message") or self.data.get("notes") or self.event_type,
            },
        }


class SyntheticLiveFeedSource:
    def __init__(self, feed_id: str = DEFAULT_FEED_ID, data_dir: Path = DATA_DIR) -> None:
        self.feed_id = feed_id
        self.path = data_dir / f"{feed_id}.jsonl"
        self.events = self._load()

    def _load(self) -> list[FeedEvent]:
        if not self.path.exists():
            raise FileNotFoundError(f"Synthetic live feed not found: {self.path}")
        events: list[FeedEvent] = []
        for line_no, line in enumerate(self.path.read_text().splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(FeedEvent.from_raw(json.loads(line)))
            except Exception as exc:
                raise ValueError(f"Invalid feed event at {self.path}:{line_no}: {exc}") from exc
        return sorted(events, key=lambda event: event.feed_time_s)

    @property
    def duration_s(self) -> float:
        return max((event.feed_time_s for event in self.events), default=0)

    def to_scenario_raw(self) -> dict[str, Any]:
        return {
            "schema_version": "neon.scenario.v1",
            "schema_profile": "minimal",
            "meta": {
                "scenario_id": self.feed_id,
                "name": "Synthetic Live Feed",
                "description": "Incoming synthetic sensor/feed observations for the minimal Arktholm decision loop.",
                "duration_s": self.duration_s,
                "feed_id": self.feed_id,
                "feed_source": str(self.path),
                "ato_ref": "ato_minimal_alpha",
                "mode_label": "feed",
            },
            "initial_state": {
                "posture": "monitoring",
                "alert_level": "normal",
                "notes": "Synthetic feed idle. Assets ready.",
            },
            "events": [event.to_engine_event() for event in self.events],
        }

    def events_up_to(self, time_s: float) -> list[dict[str, Any]]:
        return [event.__dict__ for event in self.events if event.feed_time_s <= time_s]

    def last_event(self, time_s: float) -> dict[str, Any] | None:
        seen = self.events_up_to(time_s)
        return seen[-1] if seen else None

    def next_time_after(self, time_s: float) -> float | None:
        for event in self.events:
            if event.feed_time_s > time_s:
                return event.feed_time_s
        return None
