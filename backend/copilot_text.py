"""Plain-text operator responses: strip thinking, code fences, LaTeX, and raw JSON blobs."""
from __future__ import annotations

import re
from typing import Any

from ai_provider import _clean_reasoning

_FENCE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
# Display math $$...$$
_LATEX_DDOLLAR = re.compile(r"\$\$[\s\S]{0,12000}?\$\$", re.MULTILINE)
# Single-line inline $...$ (after display blocks are gone)
_LATEX_INLINE_1L = re.compile(r"\$([^\$\n]+?)\$")
# \(...\)
_LATEX_PAREN = re.compile(r"\\\(([^\)]{0,2000})\\\)")
# \[ ... \] display
_LATEX_BRACK = re.compile(r"\\\[([\s\S]{0,8000}?)\\\]")
# Standalone line that is only JSON object/array
_LOOSE_JSON_LINE = re.compile(
    r"^\s*(\{|\[)[\s\S]{0,2000}?(\}|\])\s*$",
    re.MULTILINE,
)
_THINK_TAGS = re.compile(
    r"<think>[\s\S]*?</think>"
    r"|<thinking>[\s\S]*?</thinking>"
    r"|<reasoning>[\s\S]*?</reasoning>",
    re.IGNORECASE,
)


def sanitize_copilot_message(text: str) -> str:
    """Model output for operator UI: no chain-of-thought, fences, LaTeX, or lone JSON lines."""
    if not text or not str(text).strip():
        return text
    t = str(text)
    t = _THINK_TAGS.sub("", t)
    t = _FENCE.sub("", t)
    t = _LATEX_DDOLLAR.sub("", t)
    t = _LATEX_INLINE_1L.sub("", t)
    t = _LATEX_PAREN.sub("", t)
    t = _LATEX_BRACK.sub("", t)
    t = _clean_reasoning(t) or ""
    lines: list[str] = []
    for line in t.splitlines():
        stripped = line.strip()
        if _LOOSE_JSON_LINE.match(stripped) and (stripped.startswith(("{", "["))):
            if len(stripped) > 50:
                continue
        lines.append(line)
    t = "\n".join(lines)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def slim_track(t: Any) -> dict[str, Any]:
    """Smaller track dict for context bundles (map/rail use full elsewhere)."""
    if not isinstance(t, dict):
        return {}
    drop = {"predicted_path", "notes", "formation_hint"}
    return {k: v for k, v in t.items() if k not in drop}
