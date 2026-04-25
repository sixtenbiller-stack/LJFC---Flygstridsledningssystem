"""AI provider adapter with Gemini, Ollama, and mock fallback — never logs secrets."""
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
_ollama_host: str = "http://127.0.0.1:11434"
_provider_status: str = "fallback"
_last_error: str = ""


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _ollama_models() -> set[str]:
    try:
        import httpx

        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{_ollama_host.rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
        return {str(model.get("name", "")) for model in data.get("models", [])}
    except Exception:
        logger.exception("Failed to list Ollama models")
        return set()


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


def _resolve_ollama_model(requested: str, available: set[str]) -> str | None:
    if requested in available:
        return requested
    if ":" not in requested:
        prefixed = sorted(name for name in available if name.startswith(f"{requested}:"))
        if prefixed:
            return prefixed[0]
    return None


def init_provider() -> str:
    """Initialize the AI provider. Returns the active mode: 'ollama', 'gemini', or 'mock'."""
    global _gemini_client, _provider_mode, _model_name, _ollama_host, _provider_status, _last_error

    requested_provider = os.environ.get("AI_PROVIDER", "gemini").strip().lower()
    if requested_provider == "ollama":
        _ollama_host = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST", _ollama_host)
        _ollama_host = _ollama_host.rstrip("/")
        requested_model = os.environ.get("OLLAMA_MODEL", "gemma4")
        available = _ollama_models()
        resolved_model = _resolve_ollama_model(requested_model, available)
        if resolved_model:
            _model_name = resolved_model
            _provider_mode = "ollama"
            _provider_status = "online"
            _last_error = ""
            logger.info("Ollama provider initialized with model %s at %s", _model_name, _ollama_host)
            return _provider_mode
        _model_name = requested_model
        _last_error = f"Ollama model {requested_model} not found"
        logger.warning(
            "Ollama model %s not found at %s. Available models: %s. Falling back to mock.",
            requested_model,
            _ollama_host,
            ", ".join(sorted(available)) or "none",
        )
        _provider_mode = "mock"
        _provider_status = "fallback"
        return _provider_mode

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
        _provider_status = "fallback"
        return _provider_mode

    try:
        from google import genai
        _gemini_client = genai.Client(api_key=api_key)
        _provider_mode = "gemini"
        _provider_status = "online"
        logger.info("Gemini provider initialized with model %s", _model_name)
    except Exception:
        logger.exception("Failed to initialize Gemini SDK, falling back to mock")
        _provider_mode = "mock"
        _provider_status = "fallback"

    return _provider_mode


def get_mode() -> str:
    return _provider_mode


def get_model() -> str:
    return _model_name


def get_status() -> dict[str, str]:
    label = "TEMPLATE FALLBACK"
    if _provider_mode == "ollama" and _provider_status == "online":
        label = "LOCAL GEMMA ONLINE"
    elif _provider_status == "busy":
        label = "LOCAL GEMMA BUSY"
    elif _provider_status == "error":
        label = "LOCAL GEMMA ERROR"
    return {
        "provider": _provider_mode,
        "model": _model_name,
        "status": _provider_status,
        "label": label,
        "last_error": _last_error,
    }


def generate(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str | None:
    """Send a prompt to the active provider and return text. Returns None on failure."""
    if _provider_mode == "ollama":
        return _generate_ollama(
            prompt=prompt,
            system_instruction=system_instruction,
            json_mode=json_mode,
            max_tokens=max_tokens,
            temperature=temperature,
        )

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


def _generate_ollama(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str | None:
    global _provider_status, _last_error
    try:
        import httpx
        _provider_status = "busy"

        payload: dict[str, Any] = {
            "model": _model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_instruction:
            payload["system"] = system_instruction
        if json_mode:
            payload["format"] = "json"

        with httpx.Client(timeout=90.0) as client:
            response = client.post(f"{_ollama_host.rstrip('/')}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
        _provider_status = "online"
        _last_error = ""
        return data.get("response")
    except Exception:
        _provider_status = "error"
        _last_error = "Ollama generation failed"
        logger.exception("Ollama generation failed")
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
    return _provider_mode == "ollama" or (_provider_mode == "gemini" and _gemini_client is not None)
