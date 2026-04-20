"""Deterministic response ranking engine — bounded options per ThreatGroup."""
from __future__ import annotations

from typing import Any

from models import (
    ThreatGroup, ResponseOption, Asset,
)

_RESPONSE_TEMPLATES: list[dict[str, Any]] = [
    {
        "family": "observe_verify",
        "title": "Observe & Verify",
        "summary": "Continue monitoring with available sensors. Deploy reconnaissance UAV if available. No kinetic commitment.",
        "intended_effect": "Improve classification confidence before committing effectors",
        "reversibility": "full",
        "collateral_proxy": "none",
        "blue_force_interference": "none",
        "operator_workload": "low",
        "authority_required": "available_now",
        "base_effectiveness": 0.3,
        "base_readiness_cost": 2.0,
        "base_time_to_effect": 10,
        "cost_exchange_proxy": "very_favorable",
    },
    {
        "family": "protect_posture",
        "title": "Protective Posture",
        "summary": "Raise alert level for SAM batteries covering the threatened zone. Pre-position QRA fighters but do not commit.",
        "intended_effect": "Increase defensive readiness without committing scarce effectors",
        "reversibility": "high",
        "collateral_proxy": "none",
        "blue_force_interference": "minimal",
        "operator_workload": "low",
        "authority_required": "available_now",
        "base_effectiveness": 0.45,
        "base_readiness_cost": 8.0,
        "base_time_to_effect": 20,
        "cost_exchange_proxy": "favorable",
    },
    {
        "family": "active_defense_synthetic",
        "title": "Active Defense — Fighter Intercept",
        "summary": "Commit fighter pair to intercept highest-confidence tracks. SAM batteries provide backup coverage.",
        "intended_effect": "Intercept confirmed threats before they reach defended zone",
        "reversibility": "low",
        "collateral_proxy": "low",
        "blue_force_interference": "moderate",
        "operator_workload": "medium",
        "authority_required": "available_now",
        "base_effectiveness": 0.8,
        "base_readiness_cost": 25.0,
        "base_time_to_effect": 45,
        "cost_exchange_proxy": "neutral",
    },
    {
        "family": "mixed_response_synthetic",
        "title": "Mixed Layered Defense",
        "summary": "Fighters engage priority tracks while SAMs cover secondary axis. UAV provides forward screening.",
        "intended_effect": "Defend multiple axes simultaneously with layered coverage",
        "reversibility": "low",
        "collateral_proxy": "low",
        "blue_force_interference": "moderate",
        "operator_workload": "high",
        "authority_required": "available_now",
        "base_effectiveness": 0.85,
        "base_readiness_cost": 35.0,
        "base_time_to_effect": 50,
        "cost_exchange_proxy": "neutral",
    },
    {
        "family": "non_kinetic_disrupt_synthetic",
        "title": "Non-Kinetic Disruption (Synthetic)",
        "summary": "Electronic warfare measures to degrade threat guidance and coordination. Preserves kinetic effectors.",
        "intended_effect": "Degrade swarm coordination without expending missiles",
        "reversibility": "high",
        "collateral_proxy": "none",
        "blue_force_interference": "low",
        "operator_workload": "medium",
        "authority_required": "available_now",
        "base_effectiveness": 0.5,
        "base_readiness_cost": 5.0,
        "base_time_to_effect": 15,
        "cost_exchange_proxy": "very_favorable",
    },
    {
        "family": "hold_reserve_and_monitor",
        "title": "Hold Reserve & Monitor",
        "summary": "Maintain current posture. Reserve forces preserved for potential follow-on threats.",
        "intended_effect": "Preserve combat power for confirmed higher-priority threats",
        "reversibility": "full",
        "collateral_proxy": "none",
        "blue_force_interference": "none",
        "operator_workload": "low",
        "authority_required": "available_now",
        "base_effectiveness": 0.2,
        "base_readiness_cost": 0.0,
        "base_time_to_effect": 0,
        "cost_exchange_proxy": "very_favorable",
    },
    {
        "family": "escalate_command_review",
        "title": "Escalate to Higher Command",
        "summary": "Request guidance from higher authority before committing forces. Share assessment and recommended options.",
        "intended_effect": "Obtain authorization for response that exceeds local authority",
        "reversibility": "full",
        "collateral_proxy": "none",
        "blue_force_interference": "none",
        "operator_workload": "medium",
        "authority_required": "needs_confirmation",
        "base_effectiveness": 0.15,
        "base_readiness_cost": 0.0,
        "base_time_to_effect": 120,
        "cost_exchange_proxy": "neutral",
    },
]

_SCORING_WEIGHTS = {
    "effectiveness": 0.25,
    "time_to_effect": 0.15,
    "reversibility": 0.08,
    "readiness_cost": 0.15,
    "cost_exchange": 0.12,
    "authority_readiness": 0.10,
    "confidence_match": 0.10,
    "workload": 0.05,
}

_REVERSIBILITY_SCORE = {"full": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25, "none": 0.0}
_COST_EXCHANGE_SCORE = {"very_favorable": 1.0, "favorable": 0.75, "neutral": 0.5, "unfavorable": 0.25, "very_unfavorable": 0.0}
_WORKLOAD_SCORE = {"low": 1.0, "medium": 0.6, "high": 0.3}


class ResponseRankingEngine:
    """Produces ranked bounded response options for a ThreatGroup."""

    def __init__(self) -> None:
        pass

    def reset(self) -> None:
        pass

    def rank(
        self,
        group: ThreatGroup,
        assets: list[Asset],
        guardrails: dict[str, Any] | None = None,
        policy: dict[str, Any] | None = None,
        existing_coas: list[Any] | None = None,
    ) -> list[ResponseOption]:
        guardrails = guardrails or {}
        policy = policy or {}

        avg_readiness = sum(a.readiness for a in assets) / max(len(assets), 1)
        ready_count = sum(1 for a in assets if a.status in ("ready", "standby", "alert"))
        total_count = len(assets)

        candidates = self._generate_candidates(group, avg_readiness, ready_count, total_count)
        scored = self._score_candidates(candidates, group, avg_readiness, guardrails)

        scored.sort(key=lambda c: c[1], reverse=True)

        options: list[ResponseOption] = []
        for i, (opt, final_score) in enumerate(scored[:5]):
            opt.response_id = f"resp-{group.group_id}-{opt.response_family[:8]}"
            opt.rank = i + 1
            opt.group_id = group.group_id
            opt.source_state_id = group.source_state_id
            opt.confidence = round(self._option_confidence(opt, group), 3)
            opt.scoring_factors = {k: round(v, 3) for k, v in self._compute_factors(opt, group, avg_readiness, guardrails).items()}
            options.append(opt)

        if options:
            group.top_response_ids = [o.response_id for o in options[:3]]

        return options

    def _generate_candidates(
        self, group: ThreatGroup, avg_readiness: float, ready_count: int, total_count: int,
    ) -> list[ResponseOption]:
        candidates: list[ResponseOption] = []

        for tmpl in _RESPONSE_TEMPLATES:
            family = tmpl["family"]

            # Filter: don't offer active defense if readiness is very low
            if family in ("active_defense_synthetic", "mixed_response_synthetic") and avg_readiness < 0.3:
                continue

            # Filter: don't offer hold/observe for extremely urgent FAST-lane groups
            if family in ("hold_reserve_and_monitor", "observe_verify") and group.recommended_lane == "fast" and group.urgency_score > 0.8:
                continue

            opt = ResponseOption(
                response_id="",
                group_id="",
                response_family=family,
                title=tmpl["title"],
                summary=self._contextualize_summary(tmpl, group),
                intended_effect=tmpl["intended_effect"],
                expected_effectiveness=tmpl["base_effectiveness"],
                time_to_effect_s=tmpl["base_time_to_effect"],
                reversibility=tmpl["reversibility"],
                collateral_proxy=tmpl["collateral_proxy"],
                blue_force_interference=tmpl["blue_force_interference"],
                readiness_cost_pct=tmpl["base_readiness_cost"],
                cost_exchange_proxy=tmpl["cost_exchange_proxy"],
                operator_workload=tmpl["operator_workload"],
                authority_required=tmpl["authority_required"],
                rationale=self._build_rationale(tmpl, group),
                assumptions=[
                    "Asset availability as currently reported",
                    "Threat classification matches current assessment",
                ],
            )

            # Adjust effectiveness based on group properties
            opt = self._adjust_for_group(opt, group)
            candidates.append(opt)

        return candidates

    def _adjust_for_group(self, opt: ResponseOption, group: ThreatGroup) -> ResponseOption:
        gt = group.group_type

        # Swarm bias: prefer cheap/non-kinetic
        if gt in ("probable_swarm", "second_wave_pressure"):
            if opt.response_family in ("non_kinetic_disrupt_synthetic", "observe_verify"):
                opt.expected_effectiveness = min(1.0, opt.expected_effectiveness + 0.15)
                opt.rationale.append("Effectiveness boosted: non-kinetic preferred against swarm/saturation to preserve effectors")
            if opt.response_family == "active_defense_synthetic":
                opt.readiness_cost_pct *= 1.3
                opt.rationale.append("Cost increased: kinetic response against swarm risks effector depletion")

        # High uncertainty bias: push toward verify/escalate
        if group.confidence < 0.55 or any(f.flag == "possible_decoys" for f in group.uncertainty_flags):
            if opt.response_family in ("observe_verify", "escalate_command_review", "protect_posture"):
                opt.expected_effectiveness = min(1.0, opt.expected_effectiveness + 0.1)
                opt.rationale.append("Preferred under uncertainty: verify before committing")
            if opt.response_family in ("active_defense_synthetic", "mixed_response_synthetic"):
                opt.expected_effectiveness *= 0.85
                opt.rationale.append("Degraded: high uncertainty increases risk of wasted effectors")

        # Mixed raid: layered defense is better
        if gt == "mixed_raid_with_decoys":
            if opt.response_family == "mixed_response_synthetic":
                opt.expected_effectiveness = min(1.0, opt.expected_effectiveness + 0.1)
                opt.rationale.append("Layered defense effective against mixed raid with decoys")

        return opt

    def _score_candidates(
        self,
        candidates: list[ResponseOption],
        group: ThreatGroup,
        avg_readiness: float,
        guardrails: dict[str, Any],
    ) -> list[tuple[ResponseOption, float]]:
        scored = []
        for opt in candidates:
            factors = self._compute_factors(opt, group, avg_readiness, guardrails)
            total = sum(_SCORING_WEIGHTS.get(k, 0) * v for k, v in factors.items())
            scored.append((opt, round(total, 4)))
        return scored

    def _compute_factors(
        self,
        opt: ResponseOption,
        group: ThreatGroup,
        avg_readiness: float,
        guardrails: dict[str, Any],
    ) -> dict[str, float]:
        f: dict[str, float] = {}
        f["effectiveness"] = opt.expected_effectiveness
        max_time = 120.0
        f["time_to_effect"] = max(0, 1.0 - opt.time_to_effect_s / max_time)
        f["reversibility"] = _REVERSIBILITY_SCORE.get(opt.reversibility, 0.5)
        f["readiness_cost"] = max(0, 1.0 - opt.readiness_cost_pct / 50.0)
        f["cost_exchange"] = _COST_EXCHANGE_SCORE.get(opt.cost_exchange_proxy, 0.5)

        # Authority readiness
        if opt.authority_required == "available_now":
            f["authority_readiness"] = 1.0
        elif opt.authority_required == "needs_confirmation":
            f["authority_readiness"] = 0.4
        else:
            f["authority_readiness"] = 0.1

        # Confidence match: high-commitment options penalized under low confidence
        if opt.response_family in ("active_defense_synthetic", "mixed_response_synthetic"):
            f["confidence_match"] = group.confidence
        else:
            f["confidence_match"] = min(1.0, 0.5 + group.confidence * 0.5)

        f["workload"] = _WORKLOAD_SCORE.get(opt.operator_workload, 0.5)

        return f

    def _option_confidence(self, opt: ResponseOption, group: ThreatGroup) -> float:
        base = group.confidence
        if opt.response_family in ("observe_verify", "hold_reserve_and_monitor"):
            return min(1.0, base + 0.15)
        if opt.response_family in ("active_defense_synthetic", "mixed_response_synthetic"):
            return max(0.1, base - 0.05)
        return base

    def _contextualize_summary(self, tmpl: dict[str, Any], group: ThreatGroup) -> str:
        summary = tmpl["summary"]
        n = len(group.member_track_ids)
        zone = group.most_at_risk_object_id or "the threatened area"
        return f"{summary} (Addressing {n} tracks targeting {zone})"

    def _build_rationale(self, tmpl: dict[str, Any], group: ThreatGroup) -> list[str]:
        r: list[str] = []
        fam = tmpl["family"]
        if fam == "observe_verify":
            r.append("Preserves all effectors while improving classification")
        elif fam == "active_defense_synthetic":
            r.append("Direct intercept of highest-priority tracks")
            r.append(f"Commits fighters at {tmpl['base_readiness_cost']}% readiness cost")
        elif fam == "mixed_response_synthetic":
            r.append("Multi-layer coverage across threat axes")
            r.append("Higher readiness cost but broader protection")
        elif fam == "non_kinetic_disrupt_synthetic":
            r.append("Degrades threat coordination without expending kinetic effectors")
            r.append("Cost-favorable against mass cheap threats")
        elif fam == "hold_reserve_and_monitor":
            r.append("Zero readiness cost — preserves all combat power")
            r.append("Accepts near-term risk for strategic flexibility")
        elif fam == "escalate_command_review":
            r.append("Seeks higher authority before committing")
        elif fam == "protect_posture":
            r.append("Raises readiness without irreversible commitment")
        return r
