"""Gemini AI provider with mock fallback — never logs secrets."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("neon.gemini")

_ACCEPTED_KEY_NAMES = ["GEMINI_API_KEY", "GOOGLE_AI_STUDIO_KEY", "GOOGLE_API_KEY"]
_ENV_FILES = [".env", ".env.local", ".env.development"]

_gemini_client = None
_provider_mode: str = "mock"
_model_name: str = "gemini-2.5-flash"


def _find_api_key() -> str | None:
    for name in _ACCEPTED_KEY_NAMES:
        val = os.environ.get(name)
        if val:
            logger.info("API key found via env var %s", name)
            return val

    base = Path(__file__).resolve().parent.parent
    for ef in _ENV_FILES:
        p = base / ef
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k in _ACCEPTED_KEY_NAMES and v:
                        os.environ[k] = v
                        logger.info("API key loaded from %s via %s", ef, k)
                        return v
    return None


def init_provider() -> str:
    """Initialize the AI provider. Returns the active mode: 'gemini' or 'mock'."""
    global _gemini_client, _provider_mode, _model_name

    model_override = os.environ.get("GEMINI_MODEL")
    if model_override:
        _model_name = model_override

    api_key = _find_api_key()
    if not api_key:
        logger.warning(
            "No Gemini API key found. Checked env vars: %s and files: %s. Running in mock mode.",
            _ACCEPTED_KEY_NAMES, _ENV_FILES,
        )
        _provider_mode = "mock"
        return _provider_mode

    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        _provider_mode = "gemini"
        logger.info("Gemini provider initialized with model %s", _model_name)
    except Exception:
        logger.exception("Failed to initialize Gemini SDK, falling back to mock")
        _provider_mode = "mock"

    return _provider_mode


def get_mode() -> str:
    return _provider_mode


def get_model() -> str:
    return _model_name


def generate(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str | None:
    """Send a prompt to Gemini and return the text response. Returns None on failure."""
    if _provider_mode != "gemini" or _gemini_client is None:
        return None

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction,
        )
        if json_mode:
            config.response_mime_type = "application/json"

        response = _gemini_client.models.generate_content(
            model=_model_name,
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception:
        logger.exception("Gemini generation failed")
        return None


def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> dict[str, Any] | None:
    """Generate and parse JSON from Gemini. Returns None on failure."""
    text = generate(
        prompt=prompt,
        system_instruction=system_instruction,
        json_mode=True,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if text is None:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini JSON response after repair attempt")
            return None


def is_available() -> bool:
    return _provider_mode == "gemini" and _gemini_client is not None
