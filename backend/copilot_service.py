"""Unified Copilot service — Gemini-first with mock fallback."""
from __future__ import annotations

import json
import os
from typing import Any

import gemini_provider
from models import CourseOfAction, CoaAction, SimulationResult, SimTimelineEvent
from data_loader import load_mock_response


COA_SYSTEM_INSTRUCTION = """You are the planning module of NEON COMMAND, a tactical air-defence decision support system.
Generate exactly 3 ranked Courses of Action (COAs) as JSON.
Rules:
- Each COA must be a concrete, actionable plan
- Reference specific asset IDs, track IDs, and zone IDs from the provided state
- Include readiness cost percentage (how much of total force is committed)
- Include reserve posture description
- Rank by effectiveness: protection of defended zones is the primary metric
- Risk levels: low, medium, high
- Keep ≤75% total force commitment for any single COA"""

EXPLAIN_SYSTEM_INSTRUCTION = """You are the explanation module of NEON COMMAND.
Explain why a COA was ranked as it was. Be direct and factual.
Reference specific track IDs, scores, asset capabilities, and zone priorities.
Never hedge excessively. Cite concrete data."""

SIM_NARRATION_INSTRUCTION = """You are the simulation narrator for NEON COMMAND.
Given simulation results, provide a concise narration of what happened.
Reference specific events, assets, and outcomes."""


class CopilotService:
    def __init__(self) -> None:
        pass

    def generate_coas(
        self,
        wave: int,
        source_state_id: str,
        state_context: dict[str, Any] | None = None,
    ) -> list[CourseOfAction]:
        if gemini_provider.is_available() and state_context:
            result = self._gemini_generate_coas(wave, source_state_id, state_context)
            if result:
                return result

        return self._mock_generate_coas(wave, source_state_id)

    def explain(
        self,
        coa_id: str,
        question: str,
        source_state_id: str,
        coa_data: dict[str, Any] | None = None,
        state_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if gemini_provider.is_available() and coa_data:
            result = self._gemini_explain(coa_id, question, source_state_id, coa_data, state_context)
            if result:
                return result

        return self._mock_explain(coa_id, question, source_state_id)

    def get_situation_summary(self, wave: int, source_state_id: str) -> dict[str, Any]:
        if wave >= 2:
            raw = load_mock_response("situation_summary_wave2.json")
        else:
            raw = load_mock_response("situation_summary_wave1.json")

        if not raw:
            return {"summary": "No situation data available.", "source_state_id": source_state_id}

        raw["source_state_id"] = source_state_id
        return raw

    def simulate(
        self,
        coa_id: str,
        seed: int,
        source_state_id: str,
        wave: int = 1,
    ) -> SimulationResult:
        result = self._mock_simulate(coa_id, seed, source_state_id, wave)

        if gemini_provider.is_available() and result.narration:
            enhanced = gemini_provider.generate(
                prompt=(
                    f"Simulation results for {coa_id}:\n"
                    f"Outcome score: {result.outcome_score:.0%}\n"
                    f"Threats intercepted: {result.threats_intercepted}, missed: {result.threats_missed}\n"
                    f"Zone breaches: {result.zone_breaches}\n"
                    f"Readiness remaining: {result.readiness_remaining_pct:.0f}%\n"
                    f"Timeline events: {len(result.timeline)}\n\n"
                    "Narrate this simulation result concisely for the operator."
                ),
                system_instruction=SIM_NARRATION_INSTRUCTION,
                max_tokens=300,
            )
            if enhanced:
                result.narration = enhanced

        return result

    # ── Gemini-backed implementations ──

    def _gemini_generate_coas(
        self, wave: int, source_state_id: str, context: dict[str, Any],
    ) -> list[CourseOfAction] | None:
        prompt = (
            f"Wave: {wave}\n"
            f"State snapshot: {source_state_id}\n"
            f"Hostile tracks: {json.dumps(context.get('tracks', []), default=str)[:2000]}\n"
            f"Friendly assets: {json.dumps(context.get('assets', []), default=str)[:2000]}\n"
            f"Threat scores: {json.dumps(context.get('threat_scores', []), default=str)[:1500]}\n"
            f"Defended zones: {json.dumps(context.get('zones', []), default=str)[:1000]}\n\n"
            "Generate exactly 3 ranked COAs as a JSON object with key 'coas', each containing:\n"
            "coa_id, rank, title, summary, actions (array of {asset_id, action_type, target_track_ids, defended_zone_id}), "
            "protected_objectives, readiness_cost_pct, reserve_posture, estimated_outcome, "
            "risk_level (low/medium/high), assumptions (array of strings), rationale"
        )

        data = gemini_provider.generate_json(
            prompt=prompt,
            system_instruction=COA_SYSTEM_INSTRUCTION,
            max_tokens=3000,
            temperature=0.3,
        )

        if not data or "coas" not in data:
            return None

        try:
            coas = []
            for c in data["coas"][:3]:
                actions = [
                    CoaAction(
                        asset_id=a.get("asset_id", ""),
                        action_type=a.get("action_type", ""),
                        target_track_ids=a.get("target_track_ids", []),
                        defended_zone_id=a.get("defended_zone_id"),
                    )
                    for a in c.get("actions", [])
                ]
                coas.append(CourseOfAction(
                    coa_id=c.get("coa_id", f"coa-g{wave}-{len(coas)+1}"),
                    rank=c.get("rank", len(coas) + 1),
                    title=c.get("title", f"Option {chr(64 + len(coas) + 1)}"),
                    summary=c.get("summary", ""),
                    actions=actions,
                    protected_objectives=c.get("protected_objectives", []),
                    readiness_cost_pct=float(c.get("readiness_cost_pct", 0)),
                    reserve_posture=c.get("reserve_posture", ""),
                    estimated_outcome=c.get("estimated_outcome", ""),
                    risk_level=c.get("risk_level", "medium"),
                    assumptions=c.get("assumptions", []),
                    rationale=c.get("rationale", ""),
                    source_state_id=source_state_id,
                ))
            return coas if coas else None
        except Exception:
            return None

    def _gemini_explain(
        self,
        coa_id: str,
        question: str,
        source_state_id: str,
        coa_data: dict[str, Any],
        state_context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        prompt = (
            f"Question: {question}\n"
            f"COA being explained: {json.dumps(coa_data, default=str)[:2000]}\n"
        )
        if state_context:
            prompt += f"Current state context: {json.dumps(state_context, default=str)[:1500]}\n"

        prompt += (
            "\nProvide explanation as JSON with keys:\n"
            "- narration (string, 2-3 sentence summary)\n"
            "- explanation (object with: primary_factors [{factor, detail, data_citation}], "
            "trade_off_summary, uncertainty_notes [strings], recommendation_confidence)"
        )

        data = gemini_provider.generate_json(
            prompt=prompt,
            system_instruction=EXPLAIN_SYSTEM_INSTRUCTION,
            max_tokens=2000,
        )

        if not data:
            return None

        try:
            return {
                "coa_id": coa_id,
                "question_received": question,
                "source_state_id": source_state_id,
                "explanation": data.get("explanation", {
                    "primary_factors": [],
                    "trade_off_summary": "",
                    "uncertainty_notes": [],
                    "recommendation_confidence": "medium",
                }),
                "narration": data.get("narration", ""),
            }
        except Exception:
            return None

    # ── Mock/fallback implementations ──

    def _mock_generate_coas(self, wave: int, source_state_id: str) -> list[CourseOfAction]:
        if wave >= 2:
            raw = load_mock_response("coa_set_wave2.json")
        else:
            raw = load_mock_response("coa_set_wave1.json")

        if not raw or "coas" not in raw:
            return self._fallback_coas(wave, source_state_id)

        coas = []
        for c in raw["coas"]:
            actions = [CoaAction(**a) for a in c.get("actions", [])]
            coas.append(CourseOfAction(
                coa_id=c["coa_id"],
                rank=c["rank"],
                title=c["title"],
                summary=c["summary"],
                actions=actions,
                protected_objectives=c.get("protected_objectives", []),
                readiness_cost_pct=c.get("readiness_cost_pct", 0),
                reserve_posture=c.get("reserve_posture", ""),
                estimated_outcome=c.get("estimated_outcome", ""),
                risk_level=c.get("risk_level", "medium"),
                assumptions=c.get("assumptions", []),
                rationale=c.get("rationale", ""),
                source_state_id=source_state_id,
            ))
        return coas

    def _mock_explain(self, coa_id: str, question: str, source_state_id: str) -> dict[str, Any]:
        raw = load_mock_response("explanation_coa_ranking.json")
        if not raw:
            return self._fallback_explanation(coa_id, question, source_state_id)

        result = dict(raw)
        result["source_state_id"] = source_state_id
        result["coa_id"] = coa_id
        return result

    def _mock_simulate(self, coa_id: str, seed: int, source_state_id: str, wave: int) -> SimulationResult:
        if wave >= 2:
            raw = load_mock_response("simulation_result_wave2_optionA.json")
        else:
            raw = load_mock_response("simulation_result_optionA.json")

        if raw and "simulation_result" in raw:
            sr = raw["simulation_result"]
            timeline = [SimTimelineEvent(**e) for e in sr.get("timeline", [])]
            return SimulationResult(
                run_id=sr.get("run_id", f"sim-{coa_id}"),
                source_state_id=source_state_id,
                coa_id=coa_id,
                seed=seed,
                duration_s=sr.get("duration_s", 120),
                outcome_score=sr.get("outcome_score", 0),
                threats_intercepted=sr.get("threats_intercepted", 0),
                threats_missed=sr.get("threats_missed", 0),
                threats_monitored=sr.get("threats_monitored", 0),
                zone_breaches=sr.get("zone_breaches", 0),
                asset_losses=sr.get("asset_losses", 0),
                missiles_expended=sr.get("missiles_expended", {}),
                readiness_remaining_pct=sr.get("readiness_remaining_pct", 100),
                recovery_time_min=sr.get("recovery_time_min", 0),
                timeline=timeline,
                post_engagement_readiness=sr.get("post_engagement_readiness", {}),
                narration=raw.get("narration", ""),
            )

        return self._fallback_simulation(coa_id, seed, source_state_id)

    def _fallback_coas(self, wave: int, source_state_id: str) -> list[CourseOfAction]:
        return [
            CourseOfAction(
                coa_id=f"coa-fb-{wave}-{i}",
                rank=i,
                title=f"Fallback Option {chr(64+i)}",
                summary=f"Deterministic fallback COA {i} for wave {wave}.",
                actions=[],
                readiness_cost_pct=20.0 * i,
                risk_level=["low", "medium", "high"][i - 1],
                source_state_id=source_state_id,
            )
            for i in range(1, 4)
        ]

    def _fallback_explanation(self, coa_id: str, question: str, source_state_id: str) -> dict[str, Any]:
        return {
            "coa_id": coa_id,
            "question_received": question,
            "source_state_id": source_state_id,
            "explanation": {
                "primary_factors": [{"factor": "Heuristic ranking", "detail": "This COA was ranked by deterministic scoring."}],
                "trade_off_summary": "No detailed trade-off available in fallback mode.",
                "uncertainty_notes": ["Running in fallback mode — mock data unavailable."],
                "recommendation_confidence": "medium",
            },
            "narration": "Fallback explanation: this COA was ranked by deterministic heuristic scoring.",
        }

    def _fallback_simulation(self, coa_id: str, seed: int, source_state_id: str) -> SimulationResult:
        return SimulationResult(
            run_id=f"sim-fallback-{coa_id}",
            source_state_id=source_state_id,
            coa_id=coa_id,
            seed=seed,
            outcome_score=0.75,
            threats_intercepted=2,
            threats_missed=0,
            zone_breaches=0,
            readiness_remaining_pct=70.0,
            narration="Fallback simulation result — deterministic heuristic.",
        )
