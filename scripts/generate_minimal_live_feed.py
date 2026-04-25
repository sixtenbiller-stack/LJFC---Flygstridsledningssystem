#!/usr/bin/env python3
"""Generate the deterministic minimal synthetic live feed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_events(duration: int) -> list[dict]:
    return [
        {"feed_time_s": 0, "event_id": "feed-000", "event_type": "FEED_START", "source": "synthetic_sensor", "data": {"message": "Synthetic live feed minimal alpha online.", "feed_status": "online"}},
        {"feed_time_s": 0, "event_id": "feed-001", "event_type": "ATO_LOADED", "source": "synthetic_planning_cell", "data": {"ato_id": "ato_minimal_alpha", "message": "ATO-lite constraints loaded."}},
        {"feed_time_s": 8, "event_id": "feed-008", "event_type": "TRACK_OBSERVED", "source": "synthetic_sensor_north", "data": {"track_id": "trk-h01", "side": "hostile", "class_label": "unknown-air", "confidence": 0.42, "x_km": 165, "y_km": 575, "heading_deg": 170, "speed_class": "medium", "altitude_band": "medium", "status": "active", "detected_by": ["synthetic-sensor-north"], "predicted_path": [{"t_s": 8, "x_km": 165, "y_km": 575}, {"t_s": 45, "x_km": 198, "y_km": 500}, {"t_s": duration, "x_km": 248, "y_km": 410}], "corridor_id": "arktholm-south", "group_seed_id": "grp-min-01", "formation_hint": "paired_probe", "decoy_probability": 0.15, "rf_emitting": True, "maneuver_pattern": "steady_inbound", "source_disagreement": False}},
        {"feed_time_s": 20, "event_id": "feed-020", "event_type": "TRACK_OBSERVED", "source": "synthetic_sensor_north", "data": {"track_id": "trk-h02", "side": "hostile", "class_label": "unknown-air", "confidence": 0.5, "x_km": 215, "y_km": 580, "heading_deg": 178, "speed_class": "medium", "altitude_band": "medium", "status": "active", "detected_by": ["synthetic-sensor-north"], "predicted_path": [{"t_s": 20, "x_km": 215, "y_km": 580}, {"t_s": 45, "x_km": 226, "y_km": 520}, {"t_s": duration, "x_km": 252, "y_km": 415}], "corridor_id": "arktholm-south", "group_seed_id": "grp-min-01", "formation_hint": "paired_probe", "decoy_probability": 0.55, "rf_emitting": True, "maneuver_pattern": "steady_inbound", "source_disagreement": True}},
        {"feed_time_s": 25, "event_id": "feed-025", "event_type": "GROUP_DETECTED", "source": "synthetic_fusion", "data": {"group_id": "grp-min-01", "member_track_ids": ["trk-h01", "trk-h02"], "message": "System detects shared corridor and paired timing."}},
        {"feed_time_s": 45, "event_id": "feed-045", "event_type": "RECOMMENDATION_TRIGGERED", "source": "synthetic_decision_support", "data": {"group_id": "grp-min-01", "message": "Decision support threshold crossed."}},
        {"feed_time_s": duration, "event_id": f"feed-{duration:03d}", "event_type": "FEED_END", "source": "synthetic_sensor", "data": {"message": "Synthetic live feed complete."}},
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="Reserved for deterministic future variants.")
    parser.add_argument("--duration", type=int, default=180)
    parser.add_argument("--output", type=Path, default=Path("neon-command-data/live_feed_minimal_alpha.jsonl"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(json.dumps(event, separators=(",", ":")) for event in build_events(args.duration)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
