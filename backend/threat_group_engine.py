"""Deterministic threat grouping engine — clusters tracks into ThreatGroups."""
from __future__ import annotations

import math
from typing import Any

from models import (
    Track, DefendedZone, ThreatScoreBreakdown, ThreatGroup,
    UncertaintyFlag, SourceEvidence,
)

# Tunable thresholds
_TIMING_WINDOW_S = 20.0
_HEADING_TOLERANCE_DEG = 35.0
_SPATIAL_PROXIMITY_KM = 60.0
_CONVERGENCE_RADIUS_KM = 80.0
_FAST_LANE_CONFIDENCE = 0.65
_FAST_LANE_URGENCY = 0.55
_SPEED_KM_S = {"slow": 0.15, "medium": 0.35, "fast": 0.8}


class ThreatGroupEngine:
    """Groups hostile tracks into ThreatGroups using deterministic heuristics."""

    def __init__(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def assess(
        self,
        tracks: list[Track],
        zones: list[DefendedZone],
        scores: list[ThreatScoreBreakdown],
        current_time_s: float,
        source_state_id: str,
        creation_times: dict[str, float] | None = None,
    ) -> list[ThreatGroup]:
        hostile = [t for t in tracks if t.side == "hostile" and t.status == "active"]
        if not hostile:
            return []

        score_map = {s.track_id: s for s in scores}
        ct = creation_times or {}

        clusters = self._cluster(hostile, zones, ct)
        groups: list[ThreatGroup] = []
        for cluster in clusters:
            g = self._build_group(cluster, zones, score_map, current_time_s, source_state_id, ct)
            groups.append(g)

        groups.sort(key=lambda g: g.urgency_score, reverse=True)
        return groups

    def _cluster(
        self,
        tracks: list[Track],
        zones: list[DefendedZone],
        creation_times: dict[str, float],
    ) -> list[list[Track]]:
        """Union-find style clustering using timing, heading, spatial, and convergence affinity."""
        n = len(tracks)
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        for i in range(n):
            for j in range(i + 1, n):
                if self._affinity(tracks[i], tracks[j], zones, creation_times) >= 3:
                    union(i, j)

        clusters_map: dict[int, list[Track]] = {}
        for i in range(n):
            root = find(i)
            clusters_map.setdefault(root, []).append(tracks[i])

        return list(clusters_map.values())

    def _affinity(
        self, a: Track, b: Track, zones: list[DefendedZone], ct: dict[str, float]
    ) -> int:
        """Count affinity signals between two tracks (0-8).
        Uses extended metadata (corridor_id, group_seed_id, etc.) when available.
        Tracks from different temporal waves are penalized to prevent cross-wave merging."""
        score = 0

        ta = ct.get(a.track_id, 0)
        tb = ct.get(b.track_id, 0)
        time_gap = abs(ta - tb)

        # Timing proximity
        if time_gap <= _TIMING_WINDOW_S:
            score += 1

        # Heading alignment
        diff = abs(((b.heading_deg - a.heading_deg) + 180) % 360 - 180)
        if diff <= _HEADING_TOLERANCE_DEG:
            score += 1

        # Spatial proximity
        dist = math.hypot(a.x_km - b.x_km, a.y_km - b.y_km)
        if dist <= _SPATIAL_PROXIMITY_KM:
            score += 1

        # Convergence on same defended zone
        za = self._nearest_zone(a, zones)
        zb = self._nearest_zone(b, zones)
        if za and zb and za.id == zb.id:
            score += 1

        # Speed envelope similarity
        if a.speed_class == b.speed_class:
            score += 1

        # --- Extended metadata signals ---

        # Shared group_seed_id is a strong grouping signal
        if a.group_seed_id and b.group_seed_id and a.group_seed_id == b.group_seed_id:
            score += 2

        # Same corridor_id increases coordination confidence
        if a.corridor_id and b.corridor_id and a.corridor_id == b.corridor_id:
            score += 1

        # Cross-wave penalty: tracks created far apart in time
        if time_gap > _TIMING_WINDOW_S * 2:
            score -= 2

        return score

    def _build_group(
        self,
        cluster: list[Track],
        zones: list[DefendedZone],
        score_map: dict[str, ThreatScoreBreakdown],
        current_time_s: float,
        sid: str,
        creation_times: dict[str, float],
    ) -> ThreatGroup:
        member_ids = sorted([t.track_id for t in cluster])
        gid = "grp-" + "-".join(tid.replace("trk-", "") for tid in member_ids[:3])
        if len(member_ids) > 3:
            gid += f"+{len(member_ids) - 3}"

        # Coordination score (0-1): how many affinity signals across all pairs
        pair_count = max(len(cluster) * (len(cluster) - 1) // 2, 1)
        total_affinity = 0
        for i, a in enumerate(cluster):
            for b in cluster[i + 1:]:
                total_affinity += self._affinity(a, b, zones, creation_times)
        coordination = min(1.0, total_affinity / (pair_count * 3))

        # Confidence: average track confidence
        avg_conf = sum(t.confidence for t in cluster) / len(cluster)

        # Most at risk zone
        zone_votes: dict[str, int] = {}
        for t in cluster:
            z = self._nearest_zone(t, zones)
            if z:
                zone_votes[z.id] = zone_votes.get(z.id, 0) + 1
        most_at_risk = max(zone_votes, key=zone_votes.get) if zone_votes else None

        # Time to zone (minimum ETA across members)
        min_eta = None
        for t in cluster:
            sc = score_map.get(t.track_id)
            if sc and sc.eta_s is not None:
                if min_eta is None or sc.eta_s < min_eta:
                    min_eta = sc.eta_s

        # Urgency score (0-1)
        eta_urgency = max(0.0, min(1.0, 1.0 - ((min_eta or 300) / 300)))
        max_threat = max((score_map.get(t.track_id, ThreatScoreBreakdown(track_id="", total_score=0, priority_band="low", factors={})).total_score for t in cluster), default=0)
        urgency = 0.4 * eta_urgency + 0.3 * max_threat + 0.2 * coordination + 0.1 * (len(cluster) / 8)
        urgency = min(1.0, urgency)

        # Group type classification
        group_type = self._classify_group(cluster, coordination, avg_conf)

        # Saturation pressure (track count relative to maximum)
        saturation = min(1.0, len(cluster) / 5)

        # Leak-through risk
        leak = saturation * (1 - avg_conf) * eta_urgency

        # Uncertainty flags
        flags: list[UncertaintyFlag] = []
        low_conf_tracks = [t for t in cluster if t.confidence < 0.55]
        if low_conf_tracks:
            flags.append(UncertaintyFlag(
                flag="low_confidence_members",
                detail=f"{len(low_conf_tracks)} track(s) below confidence threshold: {', '.join(t.track_id for t in low_conf_tracks)}",
                severity="high" if len(low_conf_tracks) > len(cluster) / 2 else "medium",
            ))
        decoy_tracks = [t for t in cluster if "decoy" in t.class_label.lower()]
        high_decoy_prob = [t for t in cluster if (t.decoy_probability or 0) > 0.4]
        if decoy_tracks or high_decoy_prob:
            names = set(t.track_id for t in decoy_tracks) | set(t.track_id for t in high_decoy_prob)
            flags.append(UncertaintyFlag(
                flag="possible_decoys",
                detail=f"Decoy-suspected: {', '.join(sorted(names))}",
                severity="medium",
            ))
        if len(set(t.speed_class for t in cluster)) > 1:
            flags.append(UncertaintyFlag(
                flag="mixed_speed_classes",
                detail="Group contains mixed speed envelopes — may be diverse threat types",
                severity="low",
            ))
        # Source disagreement from extended metadata
        disagree_tracks = [t for t in cluster if t.source_disagreement]
        if disagree_tracks:
            flags.append(UncertaintyFlag(
                flag="source_disagreement",
                detail=f"Source disagreement on {len(disagree_tracks)} track(s): {', '.join(t.track_id for t in disagree_tracks)}. Classification less reliable.",
                severity="high" if len(disagree_tracks) > len(cluster) / 2 else "medium",
            ))
            avg_conf *= 0.85  # reduce effective confidence
        # RF emission pattern
        rf_tracks = [t for t in cluster if t.rf_emitting is True]
        if rf_tracks and len(rf_tracks) < len(cluster):
            flags.append(UncertaintyFlag(
                flag="mixed_rf_emission",
                detail=f"{len(rf_tracks)}/{len(cluster)} tracks RF-emitting — possible EW/decoy screen mix",
                severity="low",
            ))

        # Lane assignment
        lane = "fast"
        if avg_conf < _FAST_LANE_CONFIDENCE:
            lane = "slow"
        if urgency < _FAST_LANE_URGENCY:
            lane = "slow"
        if any(f.flag == "possible_decoys" and f.severity == "high" for f in flags):
            lane = "slow"

        # Evidence
        evidence = [
            SourceEvidence(factor="coordination", value=round(coordination, 2), detail=f"Pair affinity over {pair_count} pairs"),
            SourceEvidence(factor="avg_confidence", value=round(avg_conf, 2), detail=f"Mean track confidence"),
            SourceEvidence(factor="eta_urgency", value=round(eta_urgency, 2), detail=f"Min ETA {min_eta:.0f}s" if min_eta else "No ETA"),
            SourceEvidence(factor="saturation", value=round(saturation, 2), detail=f"{len(cluster)} tracks in group"),
        ]
        # Extended metadata evidence
        corridors = set(t.corridor_id for t in cluster if t.corridor_id)
        if corridors:
            evidence.append(SourceEvidence(factor="corridors", value=len(corridors), detail=f"Corridors: {', '.join(sorted(corridors))}"))
        seed_groups = set(t.group_seed_id for t in cluster if t.group_seed_id)
        if seed_groups:
            evidence.append(SourceEvidence(factor="seed_groups", value=len(seed_groups), detail=f"Seed IDs: {', '.join(sorted(seed_groups))}"))

        # Rationale bullets
        rationale = self._build_rationale(cluster, group_type, coordination, most_at_risk, min_eta, flags, zones)

        # Short narration
        zone_name = "unknown area"
        if most_at_risk:
            for z in zones:
                if z.id == most_at_risk:
                    zone_name = z.name
                    break

        narration = (
            f"{group_type.replace('_', ' ').title()} — {len(cluster)} tracks "
            f"targeting {zone_name}. "
            f"Confidence {avg_conf:.0%}, ETA {min_eta:.0f}s. "
            f"{'FAST' if lane == 'fast' else 'SLOW'} lane."
        ) if min_eta else (
            f"{group_type.replace('_', ' ').title()} — {len(cluster)} tracks. "
            f"Confidence {avg_conf:.0%}. {'FAST' if lane == 'fast' else 'SLOW'} lane."
        )

        # Inaction consequence
        inaction = f"Without response, {len(cluster)} tracks reach {zone_name} in ~{min_eta:.0f}s. " if min_eta else ""
        if saturation > 0.6:
            inaction += "Saturation risk is high — delayed response increases leak-through probability."
        elif urgency > 0.6:
            inaction += "High urgency — delay reduces available response options."
        else:
            inaction += "Moderate pressure — time available for verification before committing."

        return ThreatGroup(
            group_id=gid,
            member_track_ids=member_ids,
            group_type=group_type,
            coordination_score=round(coordination, 3),
            confidence=round(avg_conf, 3),
            rationale=rationale,
            short_narration=narration,
            most_at_risk_object_id=most_at_risk,
            urgency_score=round(urgency, 3),
            time_to_zone_s=round(min_eta, 1) if min_eta else None,
            leak_through_risk=round(leak, 3),
            saturation_pressure=round(saturation, 3),
            uncertainty_flags=flags,
            recommended_lane=lane,
            source_state_id=sid,
            evidence=evidence,
            inaction_consequence=inaction,
        )

    def _classify_group(self, cluster: list[Track], coordination: float, avg_conf: float) -> str:
        classes = [t.class_label.lower() for t in cluster]
        has_swarm = any("swarm" in c or "uav" in c for c in classes)
        has_decoy = any("decoy" in c for c in classes)
        has_fighter = any("fighter" in c for c in classes)
        has_cruise = any("cruise" in c for c in classes)
        has_jammer = any("jammer" in c or "ew" in c for c in classes)

        # Use formation_hint if available
        formation_hints = [t.formation_hint for t in cluster if t.formation_hint]
        has_tight_formation = any("tight" in h or "diamond" in h for h in formation_hints)
        has_spread = any("spread" in h or "dispersed" in h for h in formation_hints)

        # High decoy probability across members suggests decoy screen
        avg_decoy_prob = 0.0
        decoy_probs = [t.decoy_probability for t in cluster if t.decoy_probability is not None]
        if decoy_probs:
            avg_decoy_prob = sum(decoy_probs) / len(decoy_probs)

        if len(cluster) == 1:
            return "single_inbound"
        if has_swarm and len(cluster) >= 3:
            return "probable_swarm"
        if (has_decoy or avg_decoy_prob > 0.4) and (has_fighter or has_cruise):
            return "mixed_raid_with_decoys"
        if has_jammer and has_spread:
            return "recon_or_decoy_screen"
        if coordination >= 0.5 and len(cluster) >= 2:
            return "coordinated_probe"
        if avg_conf < 0.5 and (has_decoy or avg_decoy_prob > 0.3):
            return "recon_or_decoy_screen"
        if len(cluster) >= 4:
            return "second_wave_pressure"
        return "coordinated_probe"

    def _build_rationale(
        self, cluster: list[Track], group_type: str, coordination: float,
        most_at_risk: str | None, min_eta: float | None,
        flags: list[UncertaintyFlag], zones: list[DefendedZone],
    ) -> list[str]:
        r: list[str] = []
        r.append(f"Classified as {group_type.replace('_', ' ')} based on {len(cluster)} tracks")
        if coordination >= 0.5:
            r.append(f"High coordination score ({coordination:.0%}): shared timing, heading, and/or zone convergence")
        elif coordination >= 0.25:
            r.append(f"Moderate coordination ({coordination:.0%}): partial signal overlap")
        if most_at_risk:
            zone_name = most_at_risk
            for z in zones:
                if z.id == most_at_risk:
                    zone_name = z.name
                    break
            r.append(f"Primary target: {zone_name}")
        if min_eta is not None and min_eta < 120:
            r.append(f"Urgent: minimum ETA {min_eta:.0f}s to defended zone")
        for f in flags:
            r.append(f"⚠ {f.detail}")
        return r

    @staticmethod
    def _nearest_zone(track: Track, zones: list[DefendedZone]) -> DefendedZone | None:
        best = None
        best_dist = float("inf")
        for z in zones:
            d = math.hypot(track.x_km - z.center_km[0], track.y_km - z.center_km[1])
            if d < best_dist:
                best_dist = d
                best = z
        return best
