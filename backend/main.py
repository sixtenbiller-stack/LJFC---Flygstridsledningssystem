"""NEON COMMAND — FastAPI backend with Gemini-first AI copilot."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import gemini_provider
from models import (
    ScenarioLoadRequest, ScenarioControlRequest, CoaRequest, ExplainRequest,
    SimulateRequest, ApproveRequest, ThreatScoreBreakdown,
    CopilotCommand, CopilotResponse, CopilotStatus, FeedItem,
)
from scenario_engine import ScenarioEngine
from threat_scorer import ThreatScorer
from copilot_service import CopilotService
from simulation_engine import SimulationEngine
from audit_service import AuditService
from chief_of_staff_service import ChiefOfStaffService
from command_router import CommandRouter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("neon.main")

engine = ScenarioEngine()
scorer = ThreatScorer()
copilot = CopilotService()
simulator = SimulationEngine()
audit = AuditService()
chief = ChiefOfStaffService()
router = CommandRouter()

_current_coas: list = []
_current_scores: list[ThreatScoreBreakdown] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = gemini_provider.init_provider()
    logger.info("AI provider mode: %s (model: %s)", mode, gemini_provider.get_model())

    ticker = asyncio.create_task(engine.start_ticker(interval=0.1))
    evaluator = asyncio.create_task(_chief_evaluator_loop())
    yield
    ticker.cancel()
    evaluator.cancel()


async def _chief_evaluator_loop():
    """Periodically evaluate scenario state for Chief of Staff updates."""
    while True:
        await asyncio.sleep(2.0)
        if not engine.is_playing or not engine._scenario_id:
            continue
        try:
            state = engine.get_state()
            chief.evaluate(
                tracks=[t.model_dump() for t in state.tracks],
                assets=[a.model_dump() for a in state.assets],
                alerts=state.alerts,
                threat_scores=_current_scores,
                wave=state.wave,
                current_time_s=state.current_time_s,
                source_state_id=state.source_state_id,
                coa_count=len(_current_coas),
            )
        except Exception:
            logger.exception("Chief evaluator error")


app = FastAPI(title="NEON COMMAND", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── State endpoints ──

@app.get("/state")
def get_state(include_geo: bool = False) -> dict[str, Any]:
    global _current_scores
    state = engine.get_state(include_geo=include_geo)

    if engine.geography and engine.tracks:
        zones = engine.geography.defended_zones
        tracks = list(engine.tracks.values())
        _current_scores = scorer.score_all(tracks, zones, engine.current_time_s)
        for alert in state.alerts:
            for sc in _current_scores:
                if sc.track_id in alert.tracks:
                    alert.threat_score = max(alert.threat_score, sc.total_score)

    return state.model_dump()


@app.get("/alerts")
def get_alerts() -> list[dict[str, Any]]:
    if not _current_scores:
        return [a.model_dump() for a in engine.alerts]

    enriched = []
    for sc in _current_scores:
        track = engine.tracks.get(sc.track_id)
        if not track:
            continue
        enriched.append({
            "track_id": sc.track_id,
            "class_label": track.class_label,
            "confidence": track.confidence,
            "threat_score": sc.total_score,
            "priority_band": sc.priority_band,
            "factors": sc.factors,
            "nearest_zone_id": sc.nearest_zone_id,
            "eta_s": sc.eta_s,
            "heading_deg": track.heading_deg,
            "speed_class": track.speed_class,
            "altitude_band": track.altitude_band,
            "x_km": track.x_km,
            "y_km": track.y_km,
        })
    return enriched


@app.get("/coas")
def get_coas() -> list[dict[str, Any]]:
    return [c.model_dump() for c in _current_coas]


@app.get("/decisions")
def get_decisions() -> list[dict[str, Any]]:
    return [r.model_dump() for r in audit.get_all()]


# ── Scenario control ──

@app.post("/scenario/load")
def load_scenario(req: ScenarioLoadRequest) -> dict[str, str]:
    global _current_coas, _current_scores
    engine.load(req.scenario_id)
    _current_coas = []
    _current_scores = []
    audit.clear()
    chief.clear()
    router.clear()
    return {"status": "loaded", "scenario_id": req.scenario_id}


@app.post("/scenario/control")
def control_scenario(req: ScenarioControlRequest) -> dict[str, Any]:
    if req.action == "play":
        if req.speed is not None:
            engine.set_speed(req.speed)
        engine.play()
    elif req.action == "pause":
        engine.pause()
    elif req.action == "reset":
        global _current_coas, _current_scores
        engine.reset()
        _current_coas = []
        _current_scores = []
        audit.clear()
        chief.clear()
        router.clear()
    elif req.action == "speed" and req.speed is not None:
        engine.set_speed(req.speed)
    return {"status": "ok", "is_playing": engine.is_playing, "speed": engine.speed_multiplier}


# ── Agent / Copilot endpoints (preserved) ──

def _build_state_context() -> dict[str, Any]:
    """Build compact state context for AI calls."""
    tracks = [
        {"track_id": t.track_id, "side": t.side, "class_label": t.class_label,
         "confidence": t.confidence, "x_km": round(t.x_km, 1), "y_km": round(t.y_km, 1),
         "heading_deg": round(t.heading_deg, 1), "speed_class": t.speed_class,
         "altitude_band": t.altitude_band, "status": t.status}
        for t in engine.tracks.values()
    ]
    assets = [
        {"asset_id": a.asset_id, "asset_type": a.asset_type, "status": a.status,
         "readiness": round(a.readiness, 2), "current_assignment": a.current_assignment,
         "asset_class": a.asset_class}
        for a in engine.assets.values()
    ]
    zones = []
    if engine.geography:
        zones = [
            {"id": z.id, "name": z.name, "priority": z.priority,
             "center_km": z.center_km, "radius_km": z.radius_km}
            for z in engine.geography.defended_zones
        ]
    threat_scores = [
        {"track_id": s.track_id, "total_score": s.total_score,
         "priority_band": s.priority_band, "nearest_zone_id": s.nearest_zone_id,
         "eta_s": s.eta_s}
        for s in _current_scores
    ]
    return {
        "tracks": tracks,
        "assets": assets,
        "zones": zones,
        "threat_scores": threat_scores,
        "wave": engine.wave,
        "current_time_s": round(engine.current_time_s, 1),
        "source_state_id": engine.source_state_id,
    }


@app.post("/agent/coas")
def generate_coas(req: CoaRequest = CoaRequest()) -> dict[str, Any]:
    global _current_coas
    wave = req.wave if req.wave is not None else engine.wave
    context = _build_state_context()
    coas = copilot.generate_coas(wave=wave, source_state_id=engine.source_state_id, state_context=context)
    _current_coas = coas
    engine.clear_coa_trigger()

    chief.add_event_item(
        category="coa_generated",
        severity="info",
        title=f"{len(coas)} COAs generated for wave {wave}",
        body=f"Top option: {coas[0].title if coas else 'none'}. Review and select a plan for approval.",
        source_state_id=engine.source_state_id,
        suggested_actions=["Compare top 2", "Why this plan?", "Simulate top plan"],
        related_ids=[c.coa_id for c in coas],
    )

    return {
        "coas": [c.model_dump() for c in coas],
        "wave": wave,
        "source_state_id": engine.source_state_id,
    }


@app.post("/agent/explain")
def explain_coa(req: ExplainRequest) -> dict[str, Any]:
    coa_data = None
    for c in _current_coas:
        if c.coa_id == req.coa_id:
            coa_data = c.model_dump()
            break

    context = _build_state_context()
    return copilot.explain(
        coa_id=req.coa_id,
        question=req.question,
        source_state_id=engine.source_state_id,
        coa_data=coa_data,
        state_context=context,
    )


@app.post("/agent/simulate")
def simulate_coa(req: SimulateRequest) -> dict[str, Any]:
    coa_match = [c for c in _current_coas if c.coa_id == req.coa_id]

    if coa_match:
        result = copilot.simulate(
            coa_id=req.coa_id,
            seed=req.seed,
            source_state_id=engine.source_state_id,
            wave=engine.wave,
        )

        chief.add_event_item(
            category="sim_complete",
            severity="info",
            title=f"Simulation complete: {req.coa_id}",
            body=f"Outcome score: {result.outcome_score:.0%}. "
                 f"Intercepted: {result.threats_intercepted}, missed: {result.threats_missed}, "
                 f"breaches: {result.zone_breaches}.",
            source_state_id=engine.source_state_id,
            suggested_actions=["Approve selected plan", "Re-plan"],
            related_ids=[req.coa_id],
        )

        return result.model_dump()

    return {"error": f"COA {req.coa_id} not found"}


@app.post("/decision/approve")
def approve_coa(req: ApproveRequest) -> dict[str, Any]:
    coa_match = [c for c in _current_coas if c.coa_id == req.coa_id]
    if not coa_match:
        return {"error": f"COA {req.coa_id} not found"}

    coa = coa_match[0]
    committed_ids = [a.asset_id for a in coa.actions if a.action_type in ("intercept", "escort", "area_deny")]
    engine.commit_assets(committed_ids)

    record = audit.approve(
        coa_id=req.coa_id,
        source_state_id=engine.source_state_id,
        operator_note=req.operator_note,
        readiness_remaining_pct=100 - coa.readiness_cost_pct,
        wave=engine.wave,
    )

    chief.add_event_item(
        category="approval",
        severity="info",
        title=f"Plan approved: {coa.title}",
        body=f"COA {req.coa_id} approved by operator. "
             f"{len(committed_ids)} assets committed. "
             f"Readiness remaining: {100 - coa.readiness_cost_pct:.0f}%.",
        source_state_id=engine.source_state_id,
        related_ids=[req.coa_id] + committed_ids,
    )

    return record.model_dump()


# ── Copilot feed & command endpoints ──

@app.get("/copilot/feed")
def get_feed(since_id: str | None = None) -> list[dict[str, Any]]:
    items = chief.feed
    if since_id:
        idx = next((i for i, item in enumerate(items) if item.id == since_id), -1)
        if idx >= 0:
            items = items[idx + 1:]
    return [item.model_dump() for item in items]


@app.post("/copilot/command")
def copilot_command(cmd: CopilotCommand) -> dict[str, Any]:
    state = engine.get_state()
    state_dict = state.model_dump()
    state_dict["threat_scores"] = [s.model_dump() for s in _current_scores]

    def _tool_get_state_summary() -> dict[str, Any]:
        return {
            "wave": state.wave,
            "time_s": state.current_time_s,
            "hostile_tracks": sum(1 for t in state.tracks if t.side == "hostile"),
            "total_assets": len(state.assets),
            "ready_assets": sum(1 for a in state.assets if a.status in ("ready", "standby", "alert")),
            "recovering_assets": sum(1 for a in state.assets if a.status == "recovering"),
            "avg_readiness": round(sum(a.readiness for a in state.assets) / max(len(state.assets), 1), 2),
            "coa_trigger_pending": state.coa_trigger_pending,
        }

    def _tool_get_top_threats(limit: int = 5) -> list[dict[str, Any]]:
        return [s.model_dump() for s in _current_scores[:limit]]

    def _tool_generate_coas() -> dict[str, Any]:
        return generate_coas(CoaRequest(wave=engine.wave))

    def _tool_explain_coa(coa_id: str | None = None, question: str = "Why is this ranked first?") -> dict[str, Any]:
        raw = (coa_id or "").strip().lower()
        if raw in ("", "top", "first") and _current_coas:
            target = _current_coas[0].coa_id
        elif raw in ("", "top", "first"):
            return {"error": "No COAs available to explain."}
        else:
            target = coa_id or ""
        if not target:
            return {"error": "No COAs available to explain."}
        return explain_coa(ExplainRequest(coa_id=target, question=question))

    def _tool_simulate_coa(coa_id: str | None = None) -> dict[str, Any]:
        raw = (coa_id or "").strip().lower()
        if raw in ("", "top", "first") and _current_coas:
            target = _current_coas[0].coa_id
        elif raw in ("", "top", "first"):
            return {"error": "No COAs available to simulate."}
        else:
            target = coa_id or ""
        if not target:
            return {"error": "No COAs available to simulate."}
        return simulate_coa(SimulateRequest(coa_id=target))

    def _tool_compare_coas(ids: list[str] | None = None) -> dict[str, Any]:
        if ids and len(ids) >= 2:
            pair = [c.model_dump() for c in _current_coas if c.coa_id in ids[:2]]
        elif len(_current_coas) >= 2:
            pair = [_current_coas[0].model_dump(), _current_coas[1].model_dump()]
        else:
            return {"error": "Need at least 2 COAs to compare."}
        return {"coas": pair}

    def _tool_get_current_coas() -> list[dict[str, Any]]:
        return [c.model_dump() for c in _current_coas]

    def _tool_get_decisions() -> list[dict[str, Any]]:
        return [r.model_dump() for r in audit.get_all()]

    tools = {
        "get_state_summary": _tool_get_state_summary,
        "get_top_threats": _tool_get_top_threats,
        "generate_coas": _tool_generate_coas,
        "explain_coa": _tool_explain_coa,
        "simulate_coa": _tool_simulate_coa,
        "compare_coas": _tool_compare_coas,
        "get_current_coas": _tool_get_current_coas,
        "get_decisions": _tool_get_decisions,
    }

    response = router.route(cmd.input, state_summary=state_dict, tools=tools)

    if response.type == "coas" and response.data.get("coas"):
        pass  # COAs already set by tool

    return response.model_dump()


@app.get("/copilot/status")
def copilot_status() -> dict[str, Any]:
    return CopilotStatus(
        provider=gemini_provider.get_mode(),
        model=gemini_provider.get_model(),
        scenario_id=engine._scenario_id,
        feed_count=len(chief.feed),
        session_commands=router.session_commands,
    ).model_dump()
