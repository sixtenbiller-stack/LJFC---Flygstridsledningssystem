"""ATO-lite load, normalization, and ContextSpec wiring (synthetic data only)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ato_context_loader import (
    ATOLiteFile,
    ato_for_llm,
    ato_slim_for_ui,
    load_ato,
    load_ato_context,
    normalize_ato_to_context,
)
from command_router import (
    CommandRouter,
    ContextSpec,
    SPEC_BRIEF,
    SPEC_RECOMMEND,
    SPEC_TOP_THREATS,
    SPEC_WHAT_CHANGED,
    _get_ato_for_context,
)


REPO = Path(__file__).resolve().parent.parent
ATO_PATH = REPO / "neon-command-data" / "ato_minimal_alpha.json"
SCHEMA_PATH = REPO / "schemas" / "ato.schema.json"


def test_ato_file_exists_and_validates_pydantic() -> None:
    assert ATO_PATH.is_file()
    raw = json.loads(ATO_PATH.read_text())
    model = ATOLiteFile.model_validate(raw)
    ctx = normalize_ato_to_context(model)
    assert ctx["ato_id"] == "ato_minimal_alpha"
    assert "city-arktholm" in ctx["primary_defended_object_ids"]
    assert set(ctx["available_asset_ids"]) & {"ftr-n1", "sam-fw"}
    assert "ftr-n2" in set(ctx["reserve_asset_ids"])


def test_ato_minimal_load_helpers() -> None:
    d = load_ato("ato_minimal_alpha")
    assert "_error" not in d
    ctx = load_ato_context("ato_minimal_alpha")
    assert "ato_error" not in ctx
    assert len(ctx.get("active_missions", [])) >= 1


def test_ato_slim_for_ui_missions_preview() -> None:
    ctx = load_ato_context("ato_minimal_alpha")
    slim = ato_slim_for_ui(ctx)
    assert slim.get("mission_count", 0) >= 1
    assert len(slim.get("missions_preview") or []) >= 1


def test_ato_for_llm_slim_vs_full() -> None:
    ctx = load_ato_context("ato_minimal_alpha")
    s = ato_for_llm(ctx, "slim")
    assert s is not None
    assert "active_missions" not in s
    f = ato_for_llm(ctx, "full")
    assert f is not None
    assert "active_missions" in f
    n = ato_for_llm(ctx, "none")
    assert n is None


def test_missing_ato_fails_gracefully() -> None:
    ctx = load_ato_context("definitely_missing_file_xxx")
    assert ctx.get("ato_error")
    slim = ato_slim_for_ui(ctx)
    assert slim.get("ato_error") or slim.get("status") == "unavailable"


def test_json_schema_file_loads() -> None:
    assert SCHEMA_PATH.is_file()
    schema = json.loads(SCHEMA_PATH.read_text())
    assert schema.get("properties", {}).get("schema_version", {}).get("const") == "neon.ato.v1"


def test_contextspec_presets_ato() -> None:
    assert SPEC_TOP_THREATS.include_ato and SPEC_TOP_THREATS.ato_detail == "slim"
    assert not SPEC_WHAT_CHANGED.include_ato
    assert SPEC_RECOMMEND.include_ato and SPEC_RECOMMEND.ato_detail == "full"
    assert SPEC_BRIEF.include_ato and SPEC_BRIEF.ato_detail == "full"


def test_get_ato_for_context_lazy() -> None:
    spec = ContextSpec(max_chars=8000, include_ato=True, ato_detail="slim")
    state: dict = {"active_ato_id": "ato_minimal_alpha"}
    out = _get_ato_for_context(state, spec)
    assert out is not None
    assert out.get("ato_id") == "ato_minimal_alpha"

    spec2 = ContextSpec(max_chars=8000, include_ato=False, ato_detail="none")
    assert _get_ato_for_context(state, spec2) is None


def test_freeform_ato_heuristic() -> None:
    r = CommandRouter()
    s = r._freeform_context_spec("what does the ATO say about reserve?")
    assert s.include_ato and s.ato_detail == "full"
