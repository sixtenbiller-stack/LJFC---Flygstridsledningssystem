"""NEON COMMAND — FastAPI backend with Gemini-first AI copilot."""
from __future__ import annotations

import asyncio
import logging
import json
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from fastapi.staticfiles import StaticFiles

import gemini_provider
from models import (
    ScenarioLoadRequest, ScenarioControlRequest, CoaRequest, ExplainRequest,
    SimulateRequest, ApproveRequest, ThreatScoreBreakdown,
    CopilotCommand, CopilotResponse, CopilotStatus, FeedItem,
    ScenarioModel, PlaceableConfig,
    ThreatGroup, ResponseOption, DecisionCardSnapshot, AfterActionRecord,
)

from scenario_engine import ScenarioEngine
from threat_scorer import ThreatScorer
from copilot_service import CopilotService
from simulation_engine import SimulationEngine
from audit_service import AuditService
from chief_of_staff_service import ChiefOfStaffService
from command_router import CommandRouter
from threat_group_engine import ThreatGroupEngine
from response_ranking_engine import ResponseRankingEngine
from data_loader import load_planning_guardrails
from simulation_controller import SimulationController

from scenario_registry import discover as discover_scenarios, load_scenario_raw
from scenario_runtime import LiveSession, AVAILABLE_TEMPLATES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("neon.main")

engine = ScenarioEngine()
scorer = ThreatScorer()
copilot = CopilotService()
simulator = SimulationEngine()
sim_controller = SimulationController()
audit = AuditService()
chief = ChiefOfStaffService()
router = CommandRouter()
grouper = ThreatGroupEngine()
ranker = ResponseRankingEngine()

_current_coas: list = []
_current_scores: list[ThreatScoreBreakdown] = []
_current_groups: list[ThreatGroup] = []
_current_responses: dict[str, list[ResponseOption]] = {}
_after_action: list[AfterActionRecord] = []
_track_creation_times: dict[str, float] = {}
_live_session: LiveSession | None = None
_runtime_mode: str = "replay"  # replay | live
_scenario_origin: str = "builtin"  # builtin | generated | runtime_copy
_scenario_loaded_at: str = ""
_scenario_source_file: str = ""
_scenario_template: str = ""
_scenario_seed: int | None = None
_source_parent_scenario: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = gemini_provider.init_provider()
    logger.info("AI provider mode: %s (model: %s)", mode, gemini_provider.get_model())

    sim_controller.start()
    ticker = asyncio.create_task(_main_ticker_loop())
    evaluator = asyncio.create_task(_chief_evaluator_loop())
    yield
    ticker.cancel()
    evaluator.cancel()
    sim_controller.stop()


async def _main_ticker_loop():
    """Main loop that ticks the scenario engine and syncs simulations."""
    while True:
        try:
            # Simulation Controller ticks all active sessions (including live session)
            # The controller handles autonomous server-side execution.
            # We don't call _live_session.tick() here because the controller does it.
            
            engine.tick()
            
            # Sync engine time if in live mode
            if _runtime_mode == "live" and _live_session:
                engine.current_time_s = float(_live_session.current_time_s)
                
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in main ticker loop")
            await asyncio.sleep(1.0)


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
                groups=_current_groups,
            )
        except Exception:
            logger.exception("Chief evaluator error")


MAPS_DIR = Path(__file__).resolve().parent.parent / "neon-command-data" / "maps"
MAPS_DIR.mkdir(parents=True, exist_ok=True)
PLACEABLES_DIR = Path(__file__).resolve().parent / "placeables"

app = FastAPI(title="NEON COMMAND", version="0.5.0", lifespan=lifespan)

app.mount("/maps", StaticFiles(directory=str(MAPS_DIR)), name="maps")
app.mount("/placeables/icons", StaticFiles(directory=str(PLACEABLES_DIR)), name="placeable-icons")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── State endpoints ──

@app.get("/state")
def get_state(include_geo: bool = False) -> dict[str, Any]:
    global _current_scores, _current_groups, _current_responses
    state = engine.get_state(include_geo=include_geo)
    
    # Ensure geography is included if requested, even if not active in engine
    if include_geo and not state.geography:
        from data_loader import load_geography
        try:
            state.geography = load_geography()
        except:
            pass

    if engine.geography and engine.tracks:
        zones = engine.geography.defended_zones
        tracks = list(engine.tracks.values())
        _current_scores = scorer.score_all(tracks, zones, engine.current_time_s)
        for alert in state.alerts:
            for sc in _current_scores:
                if sc.track_id in alert.tracks:
                    alert.threat_score = max(alert.threat_score, sc.total_score)

        # Track creation times from scenario events
        for evt in engine._events:
            if evt.event_type == "TRACK_CREATED":
                tid = evt.data.get("track_id")
                if tid and tid not in _track_creation_times and evt.t_s <= engine.current_time_s:
                    _track_creation_times[tid] = evt.t_s

        # Compute threat groups
        _current_groups = grouper.assess(
            tracks, zones, _current_scores, engine.current_time_s,
            engine.source_state_id, _track_creation_times,
        )
        # Compute responses for each group
        guardrails = load_planning_guardrails()
        assets = list(engine.assets.values())
        _current_responses = {}
        for g in _current_groups:
            responses = ranker.rank(g, assets, guardrails=guardrails)
            _current_responses[g.group_id] = responses

    result = state.model_dump()
    result["mode"] = _runtime_mode
    result["runtime_mode"] = _runtime_mode
    result["scenario_origin"] = _scenario_origin
    
    # Add placeables from simulation controller
    p_objs = sim_controller.placeables.get("live", [])
    result["placeables"] = [p.to_dict() for p in p_objs]
    return result


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

def _reset_all_state():
    global _current_coas, _current_scores, _current_groups, _current_responses
    global _after_action, _track_creation_times, _live_session
    global _runtime_mode, _scenario_origin
    global _scenario_loaded_at, _scenario_source_file, _scenario_template, _scenario_seed
    global _source_parent_scenario
    _current_coas = []
    _current_scores = []
    _current_groups = []
    _current_responses = {}
    _after_action = []
    _track_creation_times = {}
    _live_session = None
    sim_controller.remove_session("live")
    if engine.geography:
        engine.geography.map_background = None
    _runtime_mode = "replay"
    _scenario_origin = "builtin"
    _scenario_loaded_at = ""
    _scenario_source_file = ""
    _scenario_template = ""
    _scenario_seed = None
    _source_parent_scenario = ""
    audit.clear()
    chief.clear()
    router.clear()
    grouper.reset()
    ranker.reset()


@app.get("/scenarios")
def list_scenarios() -> dict[str, Any]:
    return {
        "scenarios": discover_scenarios(),
        "templates": AVAILABLE_TEMPLATES,
    }

@app.get("/map-editor/placeables")
async def list_placeable_templates():
    # Use global PLACEABLES_DIR
    results = []
    if PLACEABLES_DIR.exists():
        for p in PLACEABLES_DIR.glob("*.py"):
            if p.stem in ["base", "template", "__init__"]:
                continue
            icon_path = p.with_suffix(".png")
            results.append({
                "type": p.stem,
                "icon_url": f"/placeables/icons/{icon_path.name}" if icon_path.exists() else None
            })
    return {"placeables": results}

@app.post("/map-editor/save")
async def save_scenario(scenario: ScenarioModel):
    custom_dir = Path(__file__).resolve().parent.parent / "neon-command-data" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    file_path = custom_dir / f"scenario_{scenario.scenario_id}.json"
    
    # Also update geography.json if map background is set
    if scenario.map_background:
        geo_path = Path(__file__).resolve().parent.parent / "neon-command-data" / "geography.json"
        if geo_path.exists():
            with open(geo_path, "r") as f:
                geo_data = json.load(f)
            geo_data["map_background"] = scenario.map_background
            with open(geo_path, "w") as f:
                json.dump(geo_data, f, indent=2)

    with open(file_path, "w") as f:
        f.write(scenario.model_dump_json(indent=2))
    return {"status": "success", "file_id": scenario.scenario_id}

@app.post("/map-editor/upload-map")
async def upload_map(file: UploadFile = File(...)):
    if not file.filename:
        return {"error": "No filename"}
    file_path = MAPS_DIR / file.filename
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"url": f"/api/maps/{file.filename}"}

@app.get("/map-editor/load/{file_id}")
async def load_scenario_for_editor(file_id: str):
    try:
        return load_scenario_raw(file_id)
    except FileNotFoundError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scenario not found")

@app.post("/map-editor/sync")
async def sync_editor_state(scenario: ScenarioModel):
    """Sync editor state with the live simulation for preview."""
    sim_controller.update_placeables("live", [p.model_dump() for p in scenario.placeables])
    if engine.geography:
        engine.geography.map_background = scenario.map_background
    return {"status": "synced"}





@app.post("/scenario/load")
def load_scenario_endpoint(req: ScenarioLoadRequest) -> dict[str, Any]:
    from datetime import datetime, timezone
    from fastapi import HTTPException
    global _scenario_loaded_at, _scenario_source_file, _runtime_mode, _scenario_origin
    global _scenario_template, _scenario_seed
    _reset_all_state()
    sid = req.scenario_id
    file_id = sid.replace("-", "_")
    try:
        try:
            engine.load(sid)
            from scenario_registry import DATA_DIR
            _scenario_source_file = str(DATA_DIR / f"{file_id}.json")
        except FileNotFoundError:
            raw = load_scenario_raw(file_id)
            engine.load_from_data(sid, raw)
            from scenario_registry import GENERATED_DIR, CUSTOM_DIR
            gen_path = GENERATED_DIR / f"{file_id}.json"
            cust_path = CUSTOM_DIR / f"{file_id}.json"
            if gen_path.exists():
                _scenario_source_file = str(gen_path)
            elif cust_path.exists():
                _scenario_source_file = str(cust_path)
            else:
                _scenario_source_file = file_id
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario {sid} not found")
    meta = engine.scenario_meta
    _runtime_mode = "replay"
    has_generator = meta.get("generator") is not None and meta.get("seed") is not None
    if has_generator:
        _scenario_origin = "generated"
        _scenario_template = meta.get("template", "")
        _scenario_seed = meta.get("seed")
    else:
        _scenario_origin = "builtin"
    # Load placeables from scenario file into simulation controller
    try:
        raw_data = load_scenario_raw(file_id)
        if "placeables" in raw_data:
            sim_controller.update_placeables("live", raw_data["placeables"])
            logger.info(f"Loaded {len(raw_data['placeables'])} placeables for session live")
    except:
        pass

    _scenario_loaded_at = datetime.now(timezone.utc).isoformat()
    return {"status": "loaded", "scenario_id": sid,
            "runtime_mode": _runtime_mode, "scenario_origin": _scenario_origin}


@app.post("/scenario/control")
def control_scenario(req: ScenarioControlRequest) -> dict[str, Any]:
    if req.action == "play":
        if req.speed is not None:
            engine.set_speed(req.speed)
        engine.play()
    elif req.action == "pause":
        engine.pause()
    elif req.action == "reset":
        _reset_all_state()
        engine.reset()
    elif req.action == "speed" and req.speed is not None:
        engine.set_speed(req.speed)
    return {"status": "ok", "is_playing": engine.is_playing, "speed": engine.speed_multiplier}


@app.post("/scenario/live/start")
def start_live_session(body: dict[str, Any]) -> dict[str, Any]:
    from datetime import datetime, timezone
    global _live_session, _runtime_mode, _scenario_origin, _scenario_loaded_at
    global _scenario_source_file, _source_parent_scenario
    _reset_all_state()
    file_id = body.get("file_id", "scenario_swarm_beta")
    seed = body.get("seed")
    _live_session = LiveSession(file_id, seed=seed)
    _runtime_mode = "live"
    _scenario_origin = "runtime_copy"
    _source_parent_scenario = file_id
    _scenario_loaded_at = datetime.now(timezone.utc).isoformat()
    _scenario_source_file = file_id

    sim_controller.add_session("live", _live_session)

    raw = {"meta": _live_session.get_meta(),
           "events": _live_session.get_events_for_engine()}
    engine.load_from_data(file_id, raw)

    chief.add_event_item(
        category="scenario_live",
        severity="info",
        title=f"Live mode active: {file_id}",
        body=f"Runtime session started from {file_id}. Live mutations enabled.",
        source_state_id=engine.source_state_id,
    )
    return {"status": "live_started", "session_id": _live_session.session_id,
            "file_id": file_id, "mode": "live"}


@app.post("/scenario/live/control")
def control_live(body: dict[str, Any]) -> dict[str, Any]:
    if not _live_session:
        return {"error": "No live session active"}
    action = body.get("action", "play")
    if action == "play":
        speed = body.get("speed")
        if speed:
            _live_session.set_speed(speed)
            engine.set_speed(speed)
        _live_session.play()
        engine.play()
    elif action == "pause":
        _live_session.pause()
        engine.pause()
    elif action == "reset":
        _live_session.reset()
        raw = {"meta": _live_session.get_meta(),
               "events": _live_session.get_events_for_engine()}
        engine.load_from_data(_live_session.file_id, raw)
    elif action == "set_speed":
        speed = body.get("value", 1.0)
        _live_session.set_speed(speed)
        engine.set_speed(speed)
    return {"status": "ok", "is_playing": _live_session.is_playing,
            "time_s": _live_session.current_time_s}


@app.post("/scenario/live/tick")
def tick_live(body: dict[str, Any] | None = None) -> dict[str, Any]:
    if not _live_session:
        return {"error": "No live session active"}
    body = body or {}
    dt = body.get("dt_s", 5)
    _live_session.tick(dt_s=dt)

    raw = {"meta": _live_session.get_meta(),
           "events": _live_session.get_events_for_engine()}
    engine.load_from_data(_live_session.file_id, raw)
    engine.current_time_s = _live_session.current_time_s
    engine._apply_events()

    return {"status": "ticked", "time_s": _live_session.current_time_s,
            "active_tracks": len(_live_session._mutator.state.get_active_tracks())}


@app.post("/scenario/live/inject")
def inject_live(body: dict[str, Any]) -> dict[str, Any]:
    if not _live_session:
        return {"error": "No live session active"}
    inject_type = body.get("type", "swarm")
    params = body.get("params", {})
    result = _live_session.inject(inject_type, params)

    raw = {"meta": _live_session.get_meta(),
           "events": _live_session.get_events_for_engine()}
    engine.load_from_data(_live_session.file_id, raw)
    engine.current_time_s = _live_session.current_time_s
    engine._apply_events()

    label_map = {
        "swarm": "Swarm injection",
        "second_wave": "Second wave / raid injection",
        "sensor_degrade": "Sensor degradation",
        "reclassify": "Track reclassification",
        "readiness_drop": "Readiness perturbation",
    }
    chief.add_event_item(
        category="live_injection",
        severity="warning",
        title=f"LIVE: {label_map.get(inject_type, inject_type)}",
        body=f"{label_map.get(inject_type, inject_type)} at t={_live_session.current_time_s}s. "
             f"Params: {params}. Active tracks: {len(_live_session._mutator.state.get_active_tracks())}.",
        source_state_id=engine.source_state_id,
    )
    return result


@app.get("/scenario/live/state")
def get_live_state() -> dict[str, Any]:
    if not _live_session:
        return {"error": "No live session active"}
    return _live_session.get_state_snapshot()


def _build_session_info() -> dict[str, Any]:
    """Single source of truth for active scenario/session metadata."""
    meta = engine.scenario_meta
    track_count = len(engine.tracks)
    group_count = len(_current_groups)
    status = "idle"
    if engine._scenario_id:
        if engine.is_playing:
            status = "playing"
        elif engine.current_time_s > 0:
            status = "paused"
        elif engine.current_time_s >= (meta.get("duration_s", 240) - 1):
            status = "ended"
        else:
            status = "loaded"

    mutation_log: list[dict] = []
    last_mutation_summary = None
    if _live_session:
        snap = _live_session.get_state_snapshot()
        mutation_log = snap.get("injection_log", [])
        if mutation_log:
            last_mutation_summary = mutation_log[-1]

    session: dict[str, Any] = {
        "scenario_id": engine._scenario_id,
        "scenario_label": engine._scenario_name or engine._scenario_id,
        "source_file": _scenario_source_file,
        "runtime_mode": _runtime_mode,
        "scenario_origin": _scenario_origin,
        "mode": _runtime_mode,
        "template_name": _scenario_template or meta.get("template"),
        "seed": _scenario_seed or meta.get("seed"),
        "runtime_session_id": _live_session.session_id if _live_session else None,
        "source_parent_scenario": _source_parent_scenario or None,
        "source_state_id": engine.source_state_id,
        "duration_s": meta.get("duration_s", 240),
        "current_time_s": round(engine.current_time_s, 1),
        "status": status,
        "is_playing": engine.is_playing,
        "speed_multiplier": engine.speed_multiplier,
        "description": meta.get("description", ""),
        "recommended_demo": meta.get("demo_notes", ""),
        "track_count": track_count,
        "group_count": group_count,
        "extended_schema_present": bool(meta.get("group_aware") or meta.get("extended_fields")),
        "loaded_at": _scenario_loaded_at,
        "scenario_meta": meta,
        "wave": engine.wave,
        "last_mutation_count": len(mutation_log),
        "last_mutation_summary": last_mutation_summary,
        "mutation_log": mutation_log[-10:] if mutation_log else [],
    }
    return session


@app.get("/scenario/session")
def get_session_info() -> dict[str, Any]:
    return _build_session_info()


@app.get("/scenario/mode")
def get_scenario_mode() -> dict[str, Any]:
    return _build_session_info()


@app.post("/scenario/jump")
def jump_to_event(body: dict[str, Any]) -> dict[str, Any]:
    """Jump playback to a derived operator moment, not raw event time."""
    target = body.get("target", "first_contact")
    marker_list = get_scenario_markers()
    marker_map = {m["type"]: m for m in marker_list}

    target_time: float | None = None
    label = target

    if target in marker_map:
        target_time = marker_map[target]["t_s"]
        label = marker_map[target]["label"]
    elif target == "scenario_end" and "end" in marker_map:
        target_time = max(0, marker_map["end"]["t_s"] - 5)
        label = "Near scenario end"

    if target_time is None:
        return {"error": f"No matching event for target: {target}"}

    import copy
    engine.current_time_s = target_time
    engine._events_applied_up_to = 0
    engine.tracks = {}
    engine.alerts = []
    engine.events_log = []
    engine._wave = 0
    engine._coa_trigger_pending = False
    engine._sensor_states = {}
    engine.assets = {a.asset_id: copy.deepcopy(a) for a in engine._initial_assets}
    engine.is_playing = False
    engine._apply_events()

    return {
        "status": "jumped",
        "target": target,
        "label": label,
        "time_s": round(engine.current_time_s, 1),
        "tracks_at_target": len(engine.tracks),
    }


@app.post("/scenario/seek")
def seek_to_time(body: dict[str, Any]) -> dict[str, Any]:
    """Seek playback to an arbitrary time (timeline scrub)."""
    t = body.get("time_s", 0)
    duration = engine.scenario_meta.get("duration_s", 240)
    t = max(0, min(float(t), float(duration)))

    import copy
    engine.current_time_s = t
    engine._events_applied_up_to = 0
    engine.tracks = {}
    engine.alerts = []
    engine.events_log = []
    engine._wave = 0
    engine._coa_trigger_pending = False
    engine._sensor_states = {}
    engine.assets = {a.asset_id: copy.deepcopy(a) for a in engine._initial_assets}
    engine.is_playing = False
    engine._apply_events()

    return {
        "status": "seeked",
        "time_s": round(engine.current_time_s, 1),
        "tracks_at_target": len(engine.tracks),
    }


@app.get("/scenario/markers")
def get_scenario_markers() -> list[dict[str, Any]]:
    """Derive operator-moment markers from raw scenario events.

    Key rule: markers reflect *operator-visible* moments, not internal
    generator metadata order.  first_group_visible is always >= first_contact
    so the demo flow is intuitive.
    """
    events = engine._events
    raw_first_track_t: float | None = None
    raw_first_group_t: float | None = None
    raw_second_group_t: float | None = None
    raw_coa_trigger_t: float | None = None
    raw_sensor_deg_t: float | None = None
    raw_end_t: float | None = None

    for ev in events:
        if ev.event_type == "TRACK_CREATED" and raw_first_track_t is None:
            raw_first_track_t = ev.t_s
        elif ev.event_type == "GROUP_FORMED":
            if raw_first_group_t is None:
                raw_first_group_t = ev.t_s
            elif raw_second_group_t is None and ev.t_s > raw_first_group_t + 15:
                raw_second_group_t = ev.t_s
        elif ev.event_type == "COA_TRIGGER" and raw_coa_trigger_t is None:
            raw_coa_trigger_t = ev.t_s
        elif ev.event_type == "SENSOR_DEGRADED" and raw_sensor_deg_t is None:
            raw_sensor_deg_t = ev.t_s
        elif ev.event_type == "SCENARIO_END":
            raw_end_t = ev.t_s

    markers: list[dict[str, Any]] = [
        {"t_s": 0, "type": "start", "label": "Scenario Start"},
    ]

    if raw_first_track_t is not None:
        markers.append({"t_s": raw_first_track_t, "type": "first_contact",
                         "label": "First Contact"})

    if raw_first_group_t is not None:
        visible_t = raw_first_group_t
        if raw_first_track_t is not None and raw_first_group_t < raw_first_track_t:
            visible_t = raw_first_track_t + 5
        markers.append({"t_s": visible_t, "type": "first_group",
                         "label": "First Group Visible"})

    decision_t = raw_coa_trigger_t
    if decision_t is None and raw_first_group_t is not None:
        decision_t = (markers[-1]["t_s"] if markers else 0)
        for m in markers:
            if m["type"] == "first_group":
                decision_t = m["t_s"] + 3
                break
    if decision_t is not None:
        first_contact_t = raw_first_track_t or 0
        if decision_t < first_contact_t:
            decision_t = first_contact_t + 8
        markers.append({"t_s": decision_t, "type": "first_decision",
                         "label": "Decision Point"})

    if raw_second_group_t is not None:
        markers.append({"t_s": raw_second_group_t, "type": "second_wave",
                         "label": "Second Wave"})

    if raw_sensor_deg_t is not None:
        markers.append({"t_s": raw_sensor_deg_t, "type": "sensor_degraded",
                         "label": "Sensor Degraded"})

    if raw_end_t is not None:
        markers.append({"t_s": raw_end_t, "type": "end", "label": "Scenario End"})

    markers.sort(key=lambda m: m["t_s"])
    return markers


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
        # Move from mock to actual server-side simulation execution
        coa = coa_match[0]
        zones = engine.geography.defended_zones if engine.geography else []
        
        result = simulator.run(
            coa=coa,
            tracks=engine.tracks,
            assets=engine.assets,
            zones=zones,
            source_state_id=engine.source_state_id,
            seed=req.seed,
        )

        # Still call copilot for narration if AI is available
        if gemini_provider.is_available():
            enhanced = gemini_provider.generate(
                prompt=(
                    f"Simulation results for {coa.coa_id}:\n"
                    f"Outcome score: {result.outcome_score:.0%}\n"
                    f"Threats intercepted: {result.threats_intercepted}, missed: {result.threats_missed}\n"
                    f"Zone breaches: {result.zone_breaches}\n"
                    f"Readiness remaining: {result.readiness_remaining_pct:.0f}%\n"
                    f"Timeline events: {len(result.timeline)}\n\n"
                    "Narrate this simulation result concisely for the operator."
                ),
                system_instruction="You are the simulation narrator for NEON COMMAND.Reference specific events, assets, and outcomes.",
                max_tokens=300,
            )
            if enhanced:
                result.narration = enhanced

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


# ── Threat Group / Response / Decision Card endpoints ──

@app.get("/groups")
def get_groups() -> list[dict[str, Any]]:
    return [g.model_dump() for g in _current_groups]


@app.get("/groups/{group_id}/responses")
def get_group_responses(group_id: str) -> list[dict[str, Any]]:
    return [r.model_dump() for r in _current_responses.get(group_id, [])]


@app.get("/groups/{group_id}/decision-card")
def get_decision_card(group_id: str) -> dict[str, Any]:
    import datetime
    group = next((g for g in _current_groups if g.group_id == group_id), None)
    if not group:
        return {"error": f"Group {group_id} not found"}
    responses = _current_responses.get(group_id, [])
    if not responses:
        return {"error": f"No responses for group {group_id}"}

    assets = list(engine.assets.values())
    avg_r = sum(a.readiness for a in assets) / max(len(assets), 1)
    ready = sum(1 for a in assets if a.status in ("ready", "standby", "alert"))

    card = DecisionCardSnapshot(
        card_id=f"card-{group_id}",
        group_id=group_id,
        group=group,
        recommended_response=responses[0],
        alternatives=responses[1:3],
        authority_status=responses[0].authority_required,
        reserve_impact_summary=f"Readiness {avg_r:.0%} ({ready}/{len(assets)} available). Top option costs {responses[0].readiness_cost_pct:.0f}%.",
        data_trust_level="high" if group.confidence >= 0.7 else ("medium" if group.confidence >= 0.5 else "low"),
        source_state_id=engine.source_state_id,
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
    )
    return card.model_dump()


@app.post("/groups/{group_id}/approve")
def approve_group_response(group_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    import datetime
    body = body or {}
    response_id = body.get("response_id")
    operator_action = body.get("action", "approve")
    override_reason = body.get("override_reason", "")

    group = next((g for g in _current_groups if g.group_id == group_id), None)
    if not group:
        return {"error": f"Group {group_id} not found"}

    responses = _current_responses.get(group_id, [])
    chosen = None
    if response_id:
        chosen = next((r for r in responses if r.response_id == response_id), None)
    elif responses:
        chosen = responses[0]

    if not chosen:
        return {"error": "No response selected"}

    record = AfterActionRecord(
        record_id=f"aar-{len(_after_action) + 1:03d}",
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        group_id=group_id,
        group_snapshot=group.model_dump(),
        response_chosen=chosen.response_id,
        response_family=chosen.response_family,
        operator_action=operator_action,
        override_reason=override_reason,
        readiness_after=100 - chosen.readiness_cost_pct,
        source_state_id=engine.source_state_id,
        wave=engine.wave,
    )
    _after_action.append(record)

    chief.add_event_item(
        category="group_decision",
        severity="info",
        title=f"Group {group_id}: {operator_action} — {chosen.title}",
        body=f"Operator {operator_action}d {chosen.response_family} for {group.group_type.replace('_', ' ')}. "
             f"Readiness impact: {chosen.readiness_cost_pct:.0f}%.",
        source_state_id=engine.source_state_id,
        related_ids=[group_id, chosen.response_id],
    )

    return record.model_dump()


@app.get("/after-action")
def get_after_action() -> list[dict[str, Any]]:
    return [r.model_dump() for r in _after_action]


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

    def _tool_get_groups() -> list[dict[str, Any]]:
        return [g.model_dump() for g in _current_groups]

    def _tool_get_group(group_id: str | None = None) -> dict[str, Any]:
        if not _current_groups:
            return {"error": "No threat groups available."}
        raw = (group_id or "").strip().lower()
        if raw in ("", "top", "first", "most-dangerous"):
            return _current_groups[0].model_dump()
        match = next((g for g in _current_groups if g.group_id == raw), None)
        return match.model_dump() if match else {"error": f"Group {group_id} not found"}

    def _tool_get_responses(group_id: str | None = None) -> list[dict[str, Any]]:
        raw = (group_id or "").strip().lower()
        if raw in ("", "top", "first", "most-dangerous") and _current_groups:
            gid = _current_groups[0].group_id
        elif raw and any(g.group_id == raw for g in _current_groups):
            gid = raw
        elif _current_groups:
            gid = _current_groups[0].group_id
        else:
            return []
        return [r.model_dump() for r in _current_responses.get(gid, [])]

    def _tool_get_decision_card(group_id: str | None = None) -> dict[str, Any]:
        raw = (group_id or "").strip().lower()
        if raw in ("", "top", "first") and _current_groups:
            gid = _current_groups[0].group_id
        elif raw and any(g.group_id == raw for g in _current_groups):
            gid = raw
        elif _current_groups:
            gid = _current_groups[0].group_id
        else:
            return {"error": "No groups available."}
        return get_decision_card(gid)

    def _tool_get_after_action() -> list[dict[str, Any]]:
        return [r.model_dump() for r in _after_action]

    tools = {
        "get_state_summary": _tool_get_state_summary,
        "get_top_threats": _tool_get_top_threats,
        "generate_coas": _tool_generate_coas,
        "explain_coa": _tool_explain_coa,
        "simulate_coa": _tool_simulate_coa,
        "compare_coas": _tool_compare_coas,
        "get_current_coas": _tool_get_current_coas,
        "get_decisions": _tool_get_decisions,
        "get_groups": _tool_get_groups,
        "get_group": _tool_get_group,
        "get_responses": _tool_get_responses,
        "get_decision_card": _tool_get_decision_card,
        "get_after_action": _tool_get_after_action,
        "get_session_info": _build_session_info,
        "jump_to": lambda target: jump_to_event({"target": target}),
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
