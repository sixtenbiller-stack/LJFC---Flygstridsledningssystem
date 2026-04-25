"""LLM-generated tactical narratives for threat groups and single tracks (Ollama / Gemini / LM Studio)."""
from __future__ import annotations

import json
import logging
from typing import Any

import ai_provider
from models import DefendedZone, ThreatGroup, Track

logger = logging.getLogger("neon.tactical_ai_narratives")

_GROUP_SYSTEM = """You are a tactical air-defence analysis assistant. Output only valid JSON, no markdown fences.
The JSON must follow the provided schema. Be concise, use correct track IDs, and sound like a C2 briefing — no role-play preamble."""

_TRACK_SYSTEM = """You are a tactical air-defence analyst. Give a 3–5 sentence assessment of a single contact.
Cite the figures provided. No markdown, no step-by-step reasoning."""


def enrich_threat_group_ai(
    group: ThreatGroup,
    member_tracks: list[Track],
    zones: list[DefendedZone],
) -> ThreatGroup:
    """Replace group narration fields with an LLM draft when a provider is available."""
    if not ai_provider.is_available():
        return group

    zone_names = {z.id: z.name for z in zones}
    tracks_payload: list[dict[str, Any]] = []
    for t in member_tracks:
        tracks_payload.append({
            "track_id": t.track_id,
            "class": t.class_label,
            "side": t.side,
            "confidence": round(t.confidence, 2),
            "heading_deg": round(t.heading_deg, 1),
            "speed_class": t.speed_class,
            "x_km": round(t.x_km, 2),
            "y_km": round(t.y_km, 2),
        })

    prompt = f"""Group ID: {group.group_id}
Engine classification: {group.group_type}
Member tracks (structured): {json.dumps(tracks_payload)}
Engine metrics: coordination={group.coordination_score:.2f} confidence={group.confidence:.2f} urgency={group.urgency_score:.2f}
Time to defended zone: {group.time_to_zone_s}s if known
Most at risk zone id: {group.most_at_risk_object_id} (human name: {zone_names.get(group.most_at_risk_object_id or '', '?')})
Recommended lane: {group.recommended_lane}
Saturation: {group.saturation_pressure:.0%}  Leak risk: {group.leak_through_risk:.0%}

Produce JSON with keys:
"short_narration": string (2 sentences max, executive summary for the right-hand panel)
"rationale": array of 2–5 short strings (evidence — no emojis)
"inaction_consequence": string (one sentence, risk if the operator does nothing timely)
Do not repeat the words "JSON" or "output". """

    data = ai_provider.generate_json(
        prompt=prompt,
        system_instruction=_GROUP_SYSTEM,
        max_tokens=700,
        temperature=0.25,
    )
    if not data:
        return group

    try:
        sn = str(data.get("short_narration", "")).strip()
        rlist = data.get("rationale")
        inc = str(data.get("inaction_consequence", "")).strip()
        if sn:
            r_out: list[str] = group.rationale
            if isinstance(rlist, list) and len(rlist) > 0:
                r_out = [str(x).strip() for x in rlist if str(x).strip()][:6]
            elif not r_out:
                r_out = [sn]
            return group.model_copy(
                update={
                    "short_narration": sn,
                    "rationale": r_out,
                    "inaction_consequence": inc or group.inaction_consequence,
                }
            )
    except Exception:
        logger.exception("enrich_threat_group_ai parse failed")
    return group


def track_tactical_brief(
    track: Track,
    *,
    threat_score: float | None = None,
    priority_band: str | None = None,
    nearest_zone_id: str | None = None,
    eta_s: float | None = None,
) -> str | None:
    """Short analyst paragraph for the track details popup."""
    if not ai_provider.is_available():
        return None

    extra = f"threat score {threat_score:.0%}" if threat_score is not None else "threat score n/a"
    if priority_band:
        extra += f", band {priority_band}"
    if nearest_zone_id:
        extra += f", nearest zone {nearest_zone_id}"
    if eta_s is not None:
        extra += f", ETA to zone {eta_s:.0f}s"

    prompt = f"""Track {track.track_id}:
- Class: {track.class_label}, side: {track.side}
- Position: {track.x_km:.1f}, {track.y_km:.1f} km
- Heading {track.heading_deg:.0f}°, speed {track.speed_class}, alt band {track.altitude_band}
- Classification confidence: {track.confidence:.0%}
- {extra}

Write the assessment in plain text (no JSON). """

    return ai_provider.generate(
        prompt=prompt,
        system_instruction=_TRACK_SYSTEM,
        max_tokens=320,
        temperature=0.2,
    )
