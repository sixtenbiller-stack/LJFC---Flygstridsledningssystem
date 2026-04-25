"""Chief of Staff — proactive AI feed triggered by material scenario changes."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

import gemini_provider
from models import FeedItem, ThreatScoreBreakdown, ThreatGroup


COOLDOWN_S = 4.0
THREAT_SCORE_THRESHOLD = 0.6
READINESS_DROP_THRESHOLD = 0.15

SYSTEM_INSTRUCTION = """You are the Chief of Staff AI for LJFC COMMAND, a tactical air-defence planning system.
You provide concise, direct operational updates to the human operator.
Rules:
- 1-3 short paragraphs maximum per update
- State what changed, why it matters, and suggest next action if appropriate
- Reference specific track IDs, zone names, asset IDs, and scores
- Never issue orders — only recommend and inform
- Never hedge excessively — be direct and factual
- Use military-style brevity when appropriate"""


class ChiefOfStaffService:
    def __init__(self) -> None:
        self._feed: list[FeedItem] = []
        self._last_update_time: float = 0.0
        self._last_track_count: int = 0
        self._last_wave: int = 0
        self._last_top_threat_id: str | None = None
        self._last_readiness_avg: float = 1.0
        self._last_coa_count: int = 0
        self._known_tracks: set[str] = set()
        self._high_threat_notified: set[str] = set()
        self._known_groups: set[str] = set()
        self._last_top_group_id: str | None = None
        self._counter: int = 0

    @property
    def feed(self) -> list[FeedItem]:
        return list(self._feed)

    def clear(self) -> None:
        self._feed.clear()
        self._counter = 0
        self._last_track_count = 0
        self._last_wave = 0
        self._last_top_threat_id = None
        self._last_readiness_avg = 1.0
        self._last_coa_count = 0
        self._known_tracks.clear()
        self._high_threat_notified.clear()
        self._known_groups.clear()
        self._last_top_group_id = None

    def evaluate(
        self,
        *,
        tracks: list[dict[str, Any]],
        assets: list[dict[str, Any]],
        alerts: list[Any],
        threat_scores: list[ThreatScoreBreakdown],
        wave: int,
        current_time_s: float,
        source_state_id: str,
        coa_count: int,
        groups: list[ThreatGroup] | None = None,
    ) -> list[FeedItem]:
        """Evaluate current state and emit feed items on material changes."""
        now = time.monotonic()
        new_items: list[FeedItem] = []
        groups = groups or []

        track_ids = {t.get("track_id", "") for t in tracks if t.get("side") == "hostile"}
        new_tracks = track_ids - self._known_tracks
        self._known_tracks = track_ids

        if wave > self._last_wave:
            if wave >= 2:
                item = self._make_item(
                    source_state_id=source_state_id,
                    category="wave_detected",
                    severity="critical",
                    title=f"WAVE {wave} DETECTED",
                    body=self._generate_wave_update(wave, tracks, assets, threat_scores),
                    suggested_actions=["Generate COAs", "Re-plan"],
                    related_ids=list(new_tracks)[:5],
                )
                new_items.append(item)
            self._last_wave = wave

        elif new_tracks and now - self._last_update_time > COOLDOWN_S:
            body = self._generate_new_track_update(new_tracks, tracks, threat_scores)
            item = self._make_item(
                source_state_id=source_state_id,
                category="threat_update",
                severity="warning",
                title=f"{len(new_tracks)} new track{'s' if len(new_tracks) > 1 else ''} detected",
                body=body,
                suggested_actions=["Generate COAs"] if coa_count == 0 else [],
                related_ids=list(new_tracks),
            )
            new_items.append(item)

        critical_new = [
            s for s in threat_scores
            if s.total_score >= THREAT_SCORE_THRESHOLD
            and s.track_id not in self._high_threat_notified
        ]
        if critical_new and now - self._last_update_time > COOLDOWN_S / 2:
            for s in critical_new[:2]:
                body = self._generate_threat_escalation(s, tracks)
                sev = "critical" if s.priority_band == "critical" else "warning"
                item = self._make_item(
                    source_state_id=source_state_id,
                    category="threat_update",
                    severity=sev,
                    title=f"{s.track_id} assessed {s.priority_band.upper()} ({s.total_score:.0%})",
                    body=body,
                    suggested_actions=["Generate COAs"] if coa_count == 0 else [f"/focus {s.track_id}"],
                    related_ids=[s.track_id],
                )
                new_items.append(item)
                self._high_threat_notified.add(s.track_id)

        if threat_scores:
            top = threat_scores[0]
            if top.track_id != self._last_top_threat_id and self._last_top_threat_id is not None:
                if now - self._last_update_time > COOLDOWN_S:
                    body = self._generate_top_threat_change(top, self._last_top_threat_id, threat_scores)
                    item = self._make_item(
                        source_state_id=source_state_id,
                        category="threat_update",
                        severity="warning",
                        title=f"Top threat changed: {top.track_id}",
                        body=body,
                        suggested_actions=[],
                        related_ids=[top.track_id],
                    )
                    new_items.append(item)
            self._last_top_threat_id = top.track_id

        if assets:
            avg_readiness = sum(a.get("readiness", 1.0) for a in assets) / len(assets)
            drop = self._last_readiness_avg - avg_readiness
            if drop >= READINESS_DROP_THRESHOLD and now - self._last_update_time > COOLDOWN_S:
                body = self._generate_readiness_update(assets, avg_readiness)
                item = self._make_item(
                    source_state_id=source_state_id,
                    category="readiness",
                    severity="warning",
                    title=f"Readiness dropped to {avg_readiness:.0%}",
                    body=body,
                    suggested_actions=["Re-plan"] if coa_count > 0 else [],
                    related_ids=[],
                )
                new_items.append(item)
            self._last_readiness_avg = avg_readiness

        # Group-level notifications
        if groups and now - self._last_update_time > COOLDOWN_S:
            current_group_ids = {g.group_id for g in groups}
            new_group_ids = current_group_ids - self._known_groups
            if new_group_ids:
                for g in groups:
                    if g.group_id in new_group_ids:
                        lane = g.recommended_lane.upper()
                        item = self._make_item(
                            source_state_id=source_state_id,
                            category="group_formed",
                            severity="warning" if g.recommended_lane == "fast" else "info",
                            title=f"Group formed: {g.group_id} ({g.group_type.replace('_', ' ')})",
                            body=g.short_narration,
                            suggested_actions=[f"/group {g.group_id}", f"/responses {g.group_id}"],
                            related_ids=[g.group_id] + g.member_track_ids[:3],
                        )
                        new_items.append(item)
                self._known_groups = current_group_ids

            if groups[0].group_id != self._last_top_group_id and self._last_top_group_id is not None:
                top_g = groups[0]
                item = self._make_item(
                    source_state_id=source_state_id,
                    category="group_priority_change",
                    severity="warning",
                    title=f"Top group changed: {top_g.group_id}",
                    body=f"Most urgent group is now {top_g.group_id} ({top_g.group_type.replace('_', ' ')}). "
                         f"Urgency {top_g.urgency_score:.0%}, {top_g.recommended_lane.upper()} lane.",
                    suggested_actions=[f"/group {top_g.group_id}"],
                    related_ids=[top_g.group_id],
                )
                new_items.append(item)
            if groups:
                self._last_top_group_id = groups[0].group_id

        if new_items:
            self._feed.extend(new_items)
            self._last_update_time = now
            if len(self._feed) > 100:
                self._feed = self._feed[-80:]

        return new_items

    def add_event_item(
        self,
        *,
        category: str,
        severity: str,
        title: str,
        body: str,
        source_state_id: str,
        suggested_actions: list[str] | None = None,
        related_ids: list[str] | None = None,
    ) -> FeedItem:
        """Manually add a feed item for explicit events (COA generated, sim complete, etc.)."""
        item = self._make_item(
            source_state_id=source_state_id,
            category=category,
            severity=severity,
            title=title,
            body=body,
            suggested_actions=suggested_actions or [],
            related_ids=related_ids or [],
        )
        self._feed.append(item)
        if len(self._feed) > 100:
            self._feed = self._feed[-80:]
        return item

    def _make_item(self, **kwargs: Any) -> FeedItem:
        self._counter += 1
        return FeedItem(
            id=f"feed-{self._counter:04d}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )

    def _generate_wave_update(
        self, wave: int, tracks: list[dict], assets: list[dict], scores: list[ThreatScoreBreakdown],
    ) -> str:
        result = gemini_provider.generate(
            prompt=self._build_context_prompt(
                f"Second wave (wave {wave}) has been detected with new inbound tracks. "
                f"Total hostile tracks: {sum(1 for t in tracks if t.get('side') == 'hostile')}. "
                f"Readiness pressure is increasing because wave-1 assignments may have reduced interceptor availability. "
                f"Asset readiness average: {sum(a.get('readiness', 1.0) for a in assets) / max(len(assets), 1):.0%}. "
                f"Recovering assets: {sum(1 for a in assets if a.get('status') == 'recovering')}. "
                "Provide a concise Chief of Staff update about this wave detection."
            ),
            system_instruction=SYSTEM_INSTRUCTION,
            max_tokens=300,
        )
        if result:
            return result

        hostile_count = sum(1 for t in tracks if t.get("side") == "hostile")
        recovering = sum(1 for a in assets if a.get("status") == "recovering")
        return (
            f"Second wave detected. {hostile_count} hostile tracks now active. "
            f"Readiness pressure is increasing — {recovering} assets recovering from wave 1 engagements. "
            f"Recommend immediate re-planning under updated constraints."
        )

    def _generate_new_track_update(
        self, new_ids: set[str], tracks: list[dict], scores: list[ThreatScoreBreakdown],
    ) -> str:
        score_map = {s.track_id: s for s in scores}
        lines = []
        for tid in sorted(new_ids):
            s = score_map.get(tid)
            if s:
                lines.append(f"{tid}: score {s.total_score:.0%} ({s.priority_band}), nearest zone {s.nearest_zone_id}")
            else:
                lines.append(f"{tid}: scoring pending")

        context = "; ".join(lines)
        result = gemini_provider.generate(
            prompt=self._build_context_prompt(
                f"New tracks detected: {context}. "
                "Provide a concise assessment of these new contacts."
            ),
            system_instruction=SYSTEM_INSTRUCTION,
            max_tokens=200,
        )
        if result:
            return result

        return f"New contacts: {context}. Assess threat and consider generating response plans."

    def _generate_threat_escalation(self, score: ThreatScoreBreakdown, tracks: list[dict]) -> str:
        track_data = next((t for t in tracks if t.get("track_id") == score.track_id), {})
        result = gemini_provider.generate(
            prompt=self._build_context_prompt(
                f"Track {score.track_id} has been assessed as {score.priority_band} priority "
                f"with threat score {score.total_score:.0%}. "
                f"Class: {track_data.get('class_label', 'unknown')}, "
                f"heading: {track_data.get('heading_deg', 0):.0f}°, "
                f"speed: {track_data.get('speed_class', 'unknown')}, "
                f"nearest zone: {score.nearest_zone_id}, "
                f"ETA: {score.eta_s:.0f}s. "
                f"Key factors: {', '.join(f'{k}={v:.2f}' for k, v in score.factors.items() if v > 0.3)}. "
                "Explain why this track is significant."
            ),
            system_instruction=SYSTEM_INSTRUCTION,
            max_tokens=200,
        )
        if result:
            return result

        factor_str = ", ".join(f"{k}: {v:.2f}" for k, v in score.factors.items() if v > 0.3)
        return (
            f"{score.track_id} assessed {score.priority_band} at {score.total_score:.0%}. "
            f"Nearest defended zone: {score.nearest_zone_id}, ETA {score.eta_s:.0f}s. "
            f"Key drivers: {factor_str}."
        )

    def _generate_top_threat_change(
        self, new_top: ThreatScoreBreakdown, old_id: str, scores: list[ThreatScoreBreakdown],
    ) -> str:
        result = gemini_provider.generate(
            prompt=self._build_context_prompt(
                f"The top-priority threat has changed from {old_id} to {new_top.track_id} "
                f"(score {new_top.total_score:.0%}, band {new_top.priority_band}). "
                f"Nearest zone: {new_top.nearest_zone_id}, ETA: {new_top.eta_s}s. "
                "Explain why this is significant for the operator."
            ),
            system_instruction=SYSTEM_INSTRUCTION,
            max_tokens=200,
        )
        if result:
            return result

        return (
            f"Priority shift: {new_top.track_id} now ranks highest at {new_top.total_score:.0%} "
            f"(was {old_id}). Nearest zone: {new_top.nearest_zone_id}."
        )

    def _generate_readiness_update(self, assets: list[dict], avg: float) -> str:
        recovering = [a.get("asset_id", "?") for a in assets if a.get("status") == "recovering"]
        return (
            f"Average force readiness has dropped to {avg:.0%}. "
            f"Recovering assets: {', '.join(recovering[:4])}. "
            f"Current planning options may need revision."
        )

    def _build_context_prompt(self, situation: str) -> str:
        return (
            "You are the Chief of Staff providing a concise tactical update.\n\n"
            f"SITUATION:\n{situation}\n\n"
            "Provide a 1-3 paragraph update. Be direct, reference IDs and numbers. "
            "Suggest next action if appropriate."
        )
