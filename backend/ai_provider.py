"""AI provider — Gemini (internet) and LM Studio (local) support."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("neon.ai_provider")

_ACCEPTED_KEY_NAMES = ["GEMINI_API_KEY", "GOOGLE_AI_STUDIO_KEY", "GOOGLE_API_KEY"]
_ENV_FILES = [".env", ".env.local", ".env.development"]

_gemini_client = None
_lmstudio_base_url: str | None = None
_provider_mode: str = "mock"
_model_name: str = "gemini-2.0-flash"


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
    """Initialize the AI provider. Supports 'lmstudio', 'gemini' or 'mock'."""
    global _gemini_client, _provider_mode, _model_name, _lmstudio_base_url

    # Check for LM Studio first
    lm_url = os.environ.get("LMSTUDIO_BASE_URL")
    if lm_url:
        _provider_mode = "lmstudio"
        base_url = lm_url.rstrip("/")
        # Ensure base_url includes /v1 for OpenAI compatibility if not present
        if not base_url.endswith("/v1"):
            logger.info("Appending /v1 to LMSTUDIO_BASE_URL for OpenAI compatibility")
            base_url += "/v1"
        _lmstudio_base_url = base_url
        _model_name = os.environ.get("LMSTUDIO_MODEL", "local-model")
        logger.info("LM Studio provider initialized at %s with model %s", _lmstudio_base_url, _model_name)
        return _provider_mode

    # Fallback to Gemini
    model_override = os.environ.get("GEMINI_MODEL")
    if model_override:
        _model_name = model_override

    api_key = _find_api_key()
    if not api_key:
        logger.warning(
            "No Gemini API key found and LMSTUDIO_BASE_URL not set. Running in mock mode."
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
    """Send a prompt to the active provider and return the text response."""
    if _provider_mode == "mock":
        return None

    if _provider_mode == "lmstudio":
        return _generate_lmstudio(prompt, system_instruction, json_mode, max_tokens, temperature)

    if _provider_mode == "gemini" and _gemini_client:
        return _generate_gemini(prompt, system_instruction, json_mode, max_tokens, temperature)

    return None


def _generate_gemini(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str | None:
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
        return _clean_reasoning(response.text)
    except Exception:
        logger.exception("Gemini generation failed")
        return None


def _generate_lmstudio(
    prompt: str,
    system_instruction: str | None = None,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str | None:
    import httpx
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": _model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = httpx.post(f"{_lmstudio_base_url}/chat/completions", json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _clean_reasoning(content)
    except Exception:
        logger.exception("LM Studio generation failed")
        return None


def _clean_reasoning(text: str | None) -> str | None:
    """Remove common chain-of-thought/thinking tags from model output."""
    if not text:
        return text
        
    import re

    # Handle cases where thoughts are presented as a numbered list before the final response
    # This often follows a pattern like "1. Analyze...", "2. Analyze...", etc.
    # and ends with something like "<channel|>" or "Response:"
    if "<|channel|>" in text:
        text = text.split("<|channel|>")[-1]
    elif "<channel|>" in text:
        # User's example has "<channel|>"
        text = text.split("<channel|>")[-1]
        
    # Remove <thought>...</thought> or <thinking>...</thinking> blocks
    text = re.sub(r"<(thought|thinking)>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove markers like <|channel>thought and everything following if it doesn't close (common in truncated logs)
    # or just remove the line if it's a marker.
    text = re.sub(r"<\|channel\|?>thought.*?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Thinking Process:.*?\n", "", text, flags=re.IGNORECASE)
    
    # Remove tags that might not be closed
    text = re.sub(r"<(thought|thinking)>", "", text, flags=re.IGNORECASE)

    # Handle Gemini-style thoughts if they appear in text (sometimes they start with "Thought:")
    text = re.sub(r"^Thought:.*?\n", "", text, flags=re.IGNORECASE | re.MULTILINE)

    return text.strip()


def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
) -> dict[str, Any] | None:
    """Generate and parse JSON from the active provider. Returns None on failure."""
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
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response after repair attempt")
            return None


def is_available() -> bool:
    if _provider_mode == "mock":
        return False
    if _provider_mode == "lmstudio":
        return _lmstudio_base_url is not None
    return _gemini_client is not None
