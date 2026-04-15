"""Deterministic what-if simulation engine."""
from __future__ import annotations

import math
import random
from typing import Any

from models import (
    CourseOfAction, Track, Asset, DefendedZone, SimulationResult, SimTimelineEvent,
)


class SimulationEngine:
    """Run a deterministic simulation of a COA from a frozen state snapshot."""

    def run(
        self,
        coa: CourseOfAction,
        tracks: dict[str, Track],
        assets: dict[str, Asset],
        zones: list[DefendedZone],
        source_state_id: str,
        seed: int = 42,
    ) -> SimulationResult:
        rng = random.Random(seed)
        timeline: list[SimTimelineEvent] = []
        sim_t = 0.0

        timeline.append(SimTimelineEvent(
            t_s=sim_t,
            event="SIMULATION_START",
            detail=f"State frozen at {source_state_id}. COA {coa.coa_id} applied.",
        ))

        assigned_assets = {a.asset_id for a in coa.actions}
        target_tracks = set()
        for action in coa.actions:
            target_tracks.update(action.target_track_ids)

        intercepted = 0
        missed = 0
        monitored = 0
        breaches = 0
        asset_losses = 0
        missiles_aa = 0
        missiles_sam = 0

        for action in coa.actions:
            asset = assets.get(action.asset_id)
            if not asset:
                continue

            sim_t += 5 + rng.uniform(0, 10)
            is_sam = asset.asset_type == "sam_battery"

            if action.action_type in ("intercept", "area_deny", "escort") and action.target_track_ids:
                if is_sam:
                    timeline.append(SimTimelineEvent(
                        t_s=round(sim_t, 1),
                        event="SAM_ACTIVATED",
                        detail=f"{asset.asset_id} tracking {', '.join(action.target_track_ids)}.",
                    ))
                else:
                    timeline.append(SimTimelineEvent(
                        t_s=round(sim_t, 1),
                        event="ASSET_AIRBORNE",
                        detail=f"{asset.asset_id} airborne from {asset.home_base_id}.",
                    ))

                sim_t += 20 + rng.uniform(0, 15)
                for tid in action.target_track_ids:
                    track = tracks.get(tid)
                    if not track or track.status != "active":
                        continue

                    hit_prob = 0.85 if not is_sam else 0.70
                    hit_prob += rng.uniform(-0.05, 0.05)

                    if rng.random() < hit_prob:
                        intercepted += 1
                        if is_sam:
                            missiles_sam += 2
                        else:
                            missiles_aa += 2
                        timeline.append(SimTimelineEvent(
                            t_s=round(sim_t, 1),
                            event="ENGAGEMENT_RESULT",
                            detail=f"{tid} intercepted by {asset.asset_id}. Kill confirmed.",
                        ))
                    else:
                        missed += 1
                        if is_sam:
                            missiles_sam += 2
                        else:
                            missiles_aa += 2
                        timeline.append(SimTimelineEvent(
                            t_s=round(sim_t, 1),
                            event="ENGAGEMENT_RESULT",
                            detail=f"{tid} engagement missed by {asset.asset_id}.",
                        ))
                    sim_t += 3

            elif action.action_type == "recon":
                timeline.append(SimTimelineEvent(
                    t_s=round(sim_t, 1),
                    event="RECON_DEPLOYED",
                    detail=f"{asset.asset_id} deployed for forward reconnaissance.",
                ))
                monitored += 1

        unaddressed = [
            t for t in tracks.values()
            if t.side == "hostile" and t.status == "active" and t.track_id not in target_tracks
        ]
        for t in unaddressed:
            monitored += 1
            for zone in zones:
                dist = math.hypot(t.x_km - zone.center_km[0], t.y_km - zone.center_km[1])
                if dist < zone.radius_km + 30:
                    breaches += 1
                    timeline.append(SimTimelineEvent(
                        t_s=round(sim_t + 30, 1),
                        event="ZONE_BREACH",
                        detail=f"{t.track_id} breached {zone.id} (unaddressed threat).",
                    ))
                    break

        sim_t += 30
        total_assets = len(assets)
        committed = len(assigned_assets)
        readiness_pct = round(100 * (1 - committed / max(total_assets, 1)), 1)

        timeline.append(SimTimelineEvent(
            t_s=round(sim_t, 1),
            event="SIMULATION_END",
            detail=f"Threats intercepted: {intercepted}, missed: {missed}, breaches: {breaches}. "
                   f"Readiness remaining: {readiness_pct}%.",
        ))

        outcome = max(0, min(1.0, (intercepted * 0.3 - missed * 0.2 - breaches * 0.3 + 0.4)))

        return SimulationResult(
            run_id=f"sim-{coa.coa_id}-s{seed}",
            source_state_id=source_state_id,
            coa_id=coa.coa_id,
            seed=seed,
            duration_s=round(sim_t, 1),
            outcome_score=round(outcome, 3),
            threats_intercepted=intercepted,
            threats_missed=missed,
            threats_monitored=monitored,
            zone_breaches=breaches,
            asset_losses=asset_losses,
            missiles_expended={"air_to_air": missiles_aa, "sam_missile": missiles_sam},
            readiness_remaining_pct=readiness_pct,
            recovery_time_min=25 if committed > 0 else 0,
            timeline=timeline,
            narration=f"Simulation complete for {coa.coa_id}. "
                      f"{intercepted} threats intercepted, {missed} missed, {breaches} zone breaches. "
                      f"Readiness at {readiness_pct}%.",
        )
