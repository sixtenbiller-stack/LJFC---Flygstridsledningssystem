"""ATO-lite file load, validation, and normalization to ATOContext (runtime / LLM shape)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent.parent / "neon-command-data"

ATODetail = Literal["none", "slim", "full"]


class ATOReservePolicy(BaseModel):
    min_fighter_reserve: int = 0
    min_gbad_reserve: int = 0
    reserve_rationale: str = ""


class ATOPlanningIntent(BaseModel):
    commander_intent: str = ""
    primary_defended_object_ids: list[str] = Field(default_factory=list)
    secondary_defended_object_ids: list[str] = Field(default_factory=list)
    risk_posture: str = "balanced"
    reserve_policy: ATOReservePolicy = Field(default_factory=ATOReservePolicy)


class ATOAuthority(BaseModel):
    approval_required: bool = True
    approval_role: str = "air_defence_battle_manager"
    auto_execution_allowed: bool = False


class ATOLiteFile(BaseModel):
    schema_version: str = "neon.ato.v1"
    ato_id: str
    name: str = ""
    description: str = ""
    valid_from_s: float = 0
    valid_to_s: float = 0
    planning_intent: ATOPlanningIntent
    missions: list[dict[str, Any]] = Field(default_factory=list)
    authority: ATOAuthority = Field(default_factory=ATOAuthority)
    notes: list[str] = Field(default_factory=list)


def _norm_mission_type(raw: str) -> str:
    u = (raw or "").strip().upper().replace("-", "_")
    aliases = {
        "CAP": "CAP",
        "QRA": "QRA",
        "ISR": "ISR",
        "GBAD_COVERAGE": "GBAD_COVERAGE",
        "GBAD": "GBAD_COVERAGE",
        "RESERVE": "RESERVE",
        "SUPPORT": "SUPPORT",
    }
    return aliases.get(u, u or "SUPPORT")


def _norm_mission_status(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s == "active":
        return "available"
    return s or "planned"


def normalize_ato_to_context(parsed: ATOLiteFile) -> dict[str, Any]:
    available: set[str] = set()
    reserve: set[str] = set()
    committed: set[str] = set()
    active: list[dict[str, Any]] = []

    for m in parsed.missions:
        try:
            mid = m.get("mission_id", "")
            mtype = _norm_mission_type(str(m.get("mission_type", "")))
            title = m.get("title") or m.get("name") or mid
            aids = list(m.get("assigned_asset_ids") or [])
            st = _norm_mission_status(str(m.get("status", "")))
            prot = list(m.get("protected_object_ids") or m.get("defended_object_ids") or [])

            active.append(
                {
                    "mission_id": mid,
                    "mission_type": mtype,
                    "title": str(title)[:200],
                    "asset_ids": aids,
                    "status": st,
                    "protected_object_ids": prot,
                }
            )
            for aid in aids:
                if st in ("planned", "available"):
                    available.add(aid)
                elif st == "reserve":
                    reserve.add(aid)
                elif st == "committed":
                    committed.add(aid)
        except Exception:
            continue

    auth = parsed.authority
    intent = parsed.planning_intent
    rp = intent.reserve_policy

    return {
        "ato_id": parsed.ato_id,
        "name": parsed.name,
        "commander_intent": intent.commander_intent,
        "primary_defended_object_ids": intent.primary_defended_object_ids,
        "secondary_defended_object_ids": intent.secondary_defended_object_ids,
        "risk_posture": intent.risk_posture,
        "reserve_policy": {
            "min_fighter_reserve": rp.min_fighter_reserve,
            "min_gbad_reserve": rp.min_gbad_reserve,
            "reserve_rationale": rp.reserve_rationale,
        },
        "active_missions": active,
        "available_asset_ids": sorted(available),
        "reserve_asset_ids": sorted(reserve),
        "committed_asset_ids": sorted(committed),
        "approval_required": auth.approval_required,
        "approval_role": auth.approval_role,
        "auto_execution_allowed": auth.auto_execution_allowed,
    }


def ato_slim_for_ui(ctx: dict[str, Any]) -> dict[str, Any]:
    rp = ctx.get("reserve_policy") or {}
    if ctx.get("ato_error"):
        return {
            "ato_id": ctx.get("ato_id", "ato_minimal_alpha"),
            "name": "",
            "commander_intent": ctx.get("commander_intent", ""),
            "primary_defended_object_ids": ctx.get("primary_defended_object_ids", []),
            "secondary_defended_object_ids": [],
            "risk_posture": "balanced",
            "reserve_policy": {
                "min_fighter_reserve": (rp.get("min_fighter_reserve") if isinstance(rp, dict) else 0) or 0,
                "min_gbad_reserve": (rp.get("min_gbad_reserve") if isinstance(rp, dict) else 0) or 0,
                "reserve_rationale": "",
            },
            "mission_count": 0,
            "missions_preview": [],
            "available_asset_ids": [],
            "reserve_asset_ids": [],
            "approval_required": ctx.get("approval_required", True),
            "approval_role": ctx.get("approval_role", ""),
            "auto_execution_allowed": ctx.get("auto_execution_allowed", False),
            "status": "unavailable",
            "ato_error": str(ctx.get("ato_error", ""))[:400],
        }
    missions = ctx.get("active_missions") or []
    missions_preview = [
        {
            "mission_type": m.get("mission_type", ""),
            "title": str(m.get("title", ""))[:100],
        }
        for m in missions[:8]
    ]
    return {
        "ato_id": ctx.get("ato_id", "ato_minimal_alpha"),
        "name": ctx.get("name", ""),
        "commander_intent": ctx.get("commander_intent", ""),
        "primary_defended_object_ids": ctx.get("primary_defended_object_ids", []),
        "secondary_defended_object_ids": ctx.get("secondary_defended_object_ids", []),
        "risk_posture": ctx.get("risk_posture", "balanced"),
        "reserve_policy": {
            "min_fighter_reserve": rp.get("min_fighter_reserve", 0),
            "min_gbad_reserve": rp.get("min_gbad_reserve", 0),
            "reserve_rationale": (rp.get("reserve_rationale") or "")[:240],
        },
        "mission_count": len(missions),
        "missions_preview": missions_preview,
        "available_asset_ids": (ctx.get("available_asset_ids") or [])[:12],
        "reserve_asset_ids": (ctx.get("reserve_asset_ids") or [])[:12],
        "approval_required": ctx.get("approval_required", True),
        "approval_role": ctx.get("approval_role", ""),
        "auto_execution_allowed": ctx.get("auto_execution_allowed", False),
        "status": "synthetic / active",
    }


def ato_for_llm(ctx: dict[str, Any], detail: str) -> dict[str, Any] | None:
    if detail == "none" or "ato_error" in ctx:
        return None
    if detail == "slim":
        rp = ctx.get("reserve_policy") or {}
        return {
            "ato_id": ctx.get("ato_id"),
            "name": (ctx.get("name") or "")[:120],
            "commander_intent": (ctx.get("commander_intent") or "")[:500],
            "primary_defended_object_ids": ctx.get("primary_defended_object_ids", []),
            "secondary_defended_object_ids": (ctx.get("secondary_defended_object_ids") or [])[:8],
            "risk_posture": ctx.get("risk_posture"),
            "reserve_policy": {
                "min_fighter_reserve": rp.get("min_fighter_reserve", 0),
                "min_gbad_reserve": rp.get("min_gbad_reserve", 0),
                "reserve_rationale": (str(rp.get("reserve_rationale", ""))[:280]),
            },
            "approval_required": ctx.get("approval_required"),
            "approval_role": ctx.get("approval_role"),
            "auto_execution_allowed": ctx.get("auto_execution_allowed", False),
        }
    out = {
        "ato_id": ctx.get("ato_id"),
        "name": (ctx.get("name") or "")[:200],
        "commander_intent": (ctx.get("commander_intent") or "")[:800],
        "primary_defended_object_ids": ctx.get("primary_defended_object_ids", []),
        "secondary_defended_object_ids": (ctx.get("secondary_defended_object_ids") or [])[:8],
        "risk_posture": ctx.get("risk_posture"),
        "reserve_policy": ctx.get("reserve_policy", {}),
        "active_missions": (ctx.get("active_missions") or [])[:12],
        "available_asset_ids": (ctx.get("available_asset_ids") or [])[:16],
        "reserve_asset_ids": (ctx.get("reserve_asset_ids") or [])[:16],
        "committed_asset_ids": (ctx.get("committed_asset_ids") or [])[:16],
        "approval_required": ctx.get("approval_required"),
        "approval_role": ctx.get("approval_role"),
        "auto_execution_allowed": ctx.get("auto_execution_allowed", False),
    }
    notes = ctx.get("notes")
    if isinstance(notes, list) and notes:
        out["notes"] = [str(n)[:200] for n in notes[:2]]
    return out


def load_ato(ato_id_or_filename: str = "ato_minimal_alpha") -> dict[str, Any]:
    name = ato_id_or_filename.strip()
    if not name.endswith(".json"):
        name = f"{name}.json"
    path = DATA_DIR / name
    if not path.exists():
        return {"_error": f"ATO file not found: {path}"}
    try:
        raw = json.loads(path.read_text())
        model = ATOLiteFile.model_validate(raw)
        return model.model_dump()
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"Invalid ATO file: {exc}"}


def load_ato_context(ato_id: str = "ato_minimal_alpha") -> dict[str, Any]:
    raw = load_ato(ato_id)
    if raw.get("_error"):
        return {
            "ato_error": str(raw["_error"]),
            "ato_id": ato_id,
            "commander_intent": "ATO data unavailable — use scenario defaults.",
            "primary_defended_object_ids": ["city-arktholm"],
            "reserve_policy": {"min_fighter_reserve": 1, "min_gbad_reserve": 0, "reserve_rationale": ""},
            "active_missions": [],
            "available_asset_ids": [],
            "reserve_asset_ids": [],
            "committed_asset_ids": [],
            "approval_required": True,
            "approval_role": "air_defence_battle_manager",
            "auto_execution_allowed": False,
        }
    try:
        model = ATOLiteFile.model_validate(raw)
        base = normalize_ato_to_context(model)
        if model.notes:
            base["notes"] = [n[:500] for n in model.notes[:6]]
        return base
    except Exception as exc:  # noqa: BLE001
        return {
            "ato_error": f"normalize failed: {exc}",
            "ato_id": ato_id,
            "commander_intent": "",
            "primary_defended_object_ids": [],
            "reserve_policy": {"min_fighter_reserve": 0, "min_gbad_reserve": 0, "reserve_rationale": ""},
            "active_missions": [],
            "available_asset_ids": [],
            "reserve_asset_ids": [],
            "committed_asset_ids": [],
            "approval_required": True,
            "approval_role": "air_defence_battle_manager",
            "auto_execution_allowed": False,
        }
