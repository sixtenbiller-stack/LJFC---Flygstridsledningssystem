"""Deterministic threat scoring engine using scoring_params.json weights."""
from __future__ import annotations

import math
from typing import Any

from models import Track, DefendedZone, ThreatScoreBreakdown
from data_loader import load_scoring_params


class ThreatScorer:
    def __init__(self) -> None:
        params = load_scoring_params()
        self.weights = params["scoring_weights"]
        self.speed_map: dict[str, float] = params["speed_class_map"]
        self.altitude_map: dict[str, dict] = params["altitude_band_map"]
        self.thresholds: dict[str, float] = params["threat_score_thresholds"]
        self.heading_tolerance: float = params.get("heading_tolerance_deg", 30)
        self.raid_distance: float = params.get("raid_association_distance_km", 40)
        self.raid_time_window: float = params.get("raid_association_time_window_s", 30)

    def score_track(
        self,
        track: Track,
        zones: list[DefendedZone],
        all_tracks: list[Track],
        current_time_s: float,
    ) -> ThreatScoreBreakdown:
        factors: dict[str, float] = {}

        nearest_zone, nearest_dist, eta = self._nearest_zone_info(track, zones)
        zone_id = nearest_zone.id if nearest_zone else None

        # Heading toward defended zone
        heading_score = 0.0
        if nearest_zone:
            bearing = self._bearing_to(
                track.x_km, track.y_km,
                nearest_zone.center_km[0], nearest_zone.center_km[1],
            )
            deviation = abs(self._angle_diff(track.heading_deg, bearing))
            if deviation <= self.heading_tolerance:
                heading_score = 1.0
            elif deviation <= self.heading_tolerance * 2:
                heading_score = 1.0 - (deviation - self.heading_tolerance) / self.heading_tolerance
        factors["heading_toward_defended_zone"] = heading_score

        # Time to zone inverse
        max_eta = 300.0
        if eta is not None and eta > 0:
            factors["time_to_zone_inverse"] = max(0.0, min(1.0, 1.0 - (eta / max_eta)))
        else:
            factors["time_to_zone_inverse"] = 0.0

        # Speed class factor
        factors["speed_class_factor"] = self.speed_map.get(track.speed_class, 0.5)

        # Confidence level
        factors["confidence_level"] = track.confidence

        # Target value proximity
        max_dist = 400.0
        if nearest_dist is not None:
            factors["target_value_proximity"] = max(0.0, min(1.0, 1.0 - (nearest_dist / max_dist)))
        else:
            factors["target_value_proximity"] = 0.0

        # Raid association bonus
        raid_score = 0.0
        for other in all_tracks:
            if other.track_id == track.track_id:
                continue
            d = math.hypot(track.x_km - other.x_km, track.y_km - other.y_km)
            if d <= self.raid_distance:
                raid_score = 1.0
                break
        factors["raid_association_bonus"] = raid_score

        total = sum(self.weights[k] * factors[k] for k in self.weights if k in factors)
        total = max(0.0, min(1.0, total))

        band = "low"
        for level in ["critical", "high", "medium", "low"]:
            if total >= self.thresholds[level]:
                band = level
                break

        return ThreatScoreBreakdown(
            track_id=track.track_id,
            total_score=round(total, 3),
            priority_band=band,
            factors={k: round(v, 3) for k, v in factors.items()},
            nearest_zone_id=zone_id,
            eta_s=round(eta, 1) if eta else None,
        )

    def score_all(
        self,
        tracks: list[Track],
        zones: list[DefendedZone],
        current_time_s: float,
    ) -> list[ThreatScoreBreakdown]:
        hostile = [t for t in tracks if t.side == "hostile" and t.status == "active"]
        results = [self.score_track(t, zones, hostile, current_time_s) for t in hostile]
        results.sort(key=lambda r: r.total_score, reverse=True)
        return results

    def _nearest_zone_info(
        self, track: Track, zones: list[DefendedZone]
    ) -> tuple[DefendedZone | None, float | None, float | None]:
        best_zone = None
        best_dist = float("inf")
        best_eta = None

        for zone in zones:
            cx, cy = zone.center_km
            dist = math.hypot(track.x_km - cx, track.y_km - cy)
            if dist < best_dist:
                best_dist = dist
                best_zone = zone
                speed_km_s = self._speed_km_s(track.speed_class)
                if speed_km_s > 0:
                    best_eta = max(0, (dist - zone.radius_km)) / speed_km_s
                else:
                    best_eta = 999.0

        return best_zone, best_dist, best_eta

    @staticmethod
    def _speed_km_s(speed_class: str) -> float:
        speeds = {"slow": 0.15, "medium": 0.35, "fast": 0.8}
        return speeds.get(speed_class, 0.3)

    @staticmethod
    def _bearing_to(x1: float, y1: float, x2: float, y2: float) -> float:
        dx = x2 - x1
        dy = y2 - y1
        angle = math.degrees(math.atan2(dx, -dy))  # 0 = north, clockwise
        return angle % 360

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        d = (b - a + 180) % 360 - 180
        return d
