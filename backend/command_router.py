"""Command router — maps slash commands and natural language to tool functions."""
from __future__ import annotations

import re
from typing import Any, Callable

import gemini_provider
from models import CopilotResponse


SYSTEM_INSTRUCTION = """You are the Unified Copilot for NEON COMMAND. You answer operator questions about the current tactical situation.
Rules:
- Be concise and direct — 1-3 paragraphs max
- Reference specific track IDs, asset IDs, zone names, scores, and ETAs
- Never issue orders — recommend and inform only
- Ground all answers in the provided state data
- If asked about a topic not in the data, say so clearly"""

SLASH_COMMANDS = {
    "/summary": "summary",
    "/top-threats": "top_threats",
    "/most-dangerous": "top_threats",
    "/generate-coas": "generate_coas",
    "/why": "explain_coa",
    "/simulate": "simulate_coa",
    "/compare": "compare_coas",
    "/replan": "generate_coas",
    "/what-changed": "what_changed",
    "/recommend": "recommend",
    "/focus": "focus",
    "/policy": "set_policy",
    "/reserve": "set_reserve",
    "/approve": "approve_coa",
    "/brief": "brief",
    "/help": "help",
    "/commands": "help",
    "/show-readiness": "readiness",
    "/decision-log": "decision_log",
    "/last-decision": "decision_log",
    "/state-id": "state_id",
    "/fit-theater": "ux_hint",
    "/follow": "follow_nav",
}

NL_INTENTS = [
    (r"(?:what|which)\s+(?:changed|happened|is new)", "what_changed"),
    (r"(?:which|what)\s+threat.*(?:most|greatest|biggest|worst)", "top_threats"),
    (r"(?:generate|create|make)\s+(?:plans?|coas?)", "generate_coas"),
    (r"(?:re-?plan|plan again|new plans?)", "generate_coas"),
    (r"(?:why|explain|reason).*(?:plan|coa|option|ranked|better|first)", "explain_coa"),
    (r"(?:simulate|sim|what.+if|what happens)", "simulate_coa"),
    (r"(?:compare|versus|vs\b|difference)", "compare_coas"),
    (r"(?:summary|situation|sitrep|status|brief|overview)", "summary"),
    (r"(?:recommend|suggest|best option)", "recommend"),
    (r"(?:approve|execute|confirm)\s+", "approve_coa"),
    (r"(?:focus|zoom|select|show)\s+(?:on\s+)?(\S+)", "focus"),
    (r"(?:reserve|keep.*reserve|hold)", "set_reserve"),
    (r"(?:commander.?s?\s+brief|briefing)", "brief"),
]


class CommandRouter:
    def __init__(self) -> None:
        self._session_commands: int = 0
        self._recent_commands: list[dict[str, str]] = []

    @property
    def session_commands(self) -> int:
        return self._session_commands

    def clear(self) -> None:
        self._session_commands = 0
        self._recent_commands.clear()

    def route(
        self,
        raw_input: str,
        *,
        state_summary: dict[str, Any],
        tools: dict[str, Callable[..., Any]],
    ) -> CopilotResponse:
        """Parse input, determine intent, call appropriate tool, return response."""
        self._session_commands += 1
        self._recent_commands.append({"input": raw_input, "intent": ""})
        if len(self._recent_commands) > 20:
            self._recent_commands = self._recent_commands[-15:]

        text = raw_input.strip()
        intent, args = self._parse(text)
        self._recent_commands[-1]["intent"] = intent

        source_state_id = state_summary.get("source_state_id", "")

        if intent == "help":
            return self._handle_help(source_state_id)
        elif intent == "readiness":
            return self._handle_readiness(state_summary, source_state_id)
        elif intent == "decision_log":
            return self._handle_decision_log(tools, source_state_id)
        elif intent == "state_id":
            return CopilotResponse(
                type="text",
                message=f"Current snapshot lineage: {source_state_id}",
                source_state_id=source_state_id,
            )
        elif intent == "ux_hint":
            return CopilotResponse(
                type="text",
                message="Use the map toolbar: Fit theater, Focus selection, and Follow top threat are client-side controls next to the tactical display.",
                source_state_id=source_state_id,
            )
        elif intent == "follow_nav":
            return CopilotResponse(
                type="text",
                message="Toggle “Follow top threat” on the map toolbar, or click a track in the threat queue to focus.",
                source_state_id=source_state_id,
            )
        elif intent == "summary":
            return self._handle_summary(state_summary, tools, source_state_id)
        elif intent == "top_threats":
            return self._handle_top_threats(state_summary, tools, source_state_id)
        elif intent == "generate_coas":
            return self._handle_generate_coas(tools, source_state_id, text)
        elif intent == "explain_coa":
            return self._handle_explain(args, state_summary, tools, source_state_id, text)
        elif intent == "simulate_coa":
            return self._handle_simulate(args, tools, source_state_id)
        elif intent == "compare_coas":
            return self._handle_compare(args, state_summary, tools, source_state_id)
        elif intent == "what_changed":
            return self._handle_what_changed(state_summary, source_state_id)
        elif intent == "recommend":
            return self._handle_recommend(state_summary, tools, source_state_id)
        elif intent == "focus":
            return self._handle_focus(args, state_summary, source_state_id)
        elif intent == "approve_coa":
            return self._handle_approve(args, tools, source_state_id)
        elif intent == "brief":
            return self._handle_brief(state_summary, tools, source_state_id)
        elif intent == "set_reserve":
            return self._handle_set_reserve(args, source_state_id)
        elif intent == "set_policy":
            return self._handle_set_policy(args, source_state_id)
        elif intent == "freeform":
            return self._handle_freeform(text, state_summary, source_state_id)
        else:
            return CopilotResponse(
                type="error",
                message=f"Unknown command: {text}",
                source_state_id=source_state_id,
            )

    def _parse(self, text: str) -> tuple[str, list[str]]:
        if text.startswith("/"):
            parts = text.split()
            cmd = parts[0].lower()
            args = parts[1:]
            if cmd in SLASH_COMMANDS:
                return SLASH_COMMANDS[cmd], args
            return "unknown", []

        lower = text.lower()
        for pattern, intent in NL_INTENTS:
            m = re.search(pattern, lower)
            if m:
                args = list(m.groups()) if m.groups() else []
                return intent, args

        return "freeform", []

    def _handle_summary(self, state: dict, tools: dict, sid: str) -> CopilotResponse:
        summary_fn = tools.get("get_state_summary")
        if summary_fn:
            data = summary_fn()
        else:
            data = self._build_basic_summary(state)

        prompt = (
            f"Current state data:\n{_fmt(data)}\n\n"
            "Provide a concise situation summary for the operator."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            msg = self._format_summary_fallback(data)

        return CopilotResponse(
            type="text", message=msg, data=data, source_state_id=sid,
            suggested_actions=self._suggest_from_state(state),
        )

    def _handle_top_threats(self, state: dict, tools: dict, sid: str) -> CopilotResponse:
        get_threats = tools.get("get_top_threats")
        threats = get_threats(5) if get_threats else []

        if not threats:
            return CopilotResponse(
                type="text", message="No hostile tracks currently detected.",
                source_state_id=sid,
            )

        prompt = (
            f"Current threat assessment:\n{_fmt(threats)}\n\n"
            "Summarize the top threats for the operator. Reference track IDs, scores, zones, and ETAs."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            lines = []
            for t in threats[:5]:
                if isinstance(t, dict):
                    lines.append(
                        f"• {t.get('track_id', '?')}: {t.get('priority_band', '?')} "
                        f"({t.get('total_score', 0):.0%}), zone {t.get('nearest_zone_id', '?')}, "
                        f"ETA {t.get('eta_s', '?')}s"
                    )
            msg = "Top threats:\n" + "\n".join(lines) if lines else "No detailed threat data."

        return CopilotResponse(
            type="text", message=msg, data={"threats": threats}, source_state_id=sid,
            suggested_actions=["Generate COAs"],
        )

    def _handle_generate_coas(self, tools: dict, sid: str, text: str) -> CopilotResponse:
        gen_fn = tools.get("generate_coas")
        if not gen_fn:
            return CopilotResponse(type="error", message="COA generation not available.", source_state_id=sid)

        result = gen_fn()
        return CopilotResponse(
            type="coas", message=f"Generated {len(result.get('coas', []))} COAs.",
            data=result, source_state_id=sid,
            suggested_actions=["Compare top 2", "Why this plan?", "Simulate top plan"],
        )

    def _handle_help(self, sid: str) -> CopilotResponse:
        msg = (
            "Commands (slash + Enter):\n"
            "• Situation: /brief /summary /what-changed /top-threats /show-readiness\n"
            "• Planning: /generate-coas /recommend /replan\n"
            "• Explain/Compare: /why top | /compare (top2)\n"
            "• Simulation: /simulate top | /simulate <coa_id>\n"
            "• Policy: /policy <name> /reserve <n>\n"
            "• Focus: /focus <id>\n"
            "• Audit: /decision-log /state-id\n"
            "Map: use on-map toolbar for Fit / Focus / Follow."
        )
        return CopilotResponse(type="text", message=msg, source_state_id=sid)

    def _handle_readiness(self, state: dict, sid: str) -> CopilotResponse:
        assets = state.get("assets", [])
        if not assets:
            return CopilotResponse(type="text", message="No asset data.", source_state_id=sid)
        lines = []
        for a in assets[:20]:
            aid = a.get("asset_id", "?")
            st = a.get("status", "?")
            rd = a.get("readiness", 0)
            lines.append(f"• {aid}: {st}, readiness {float(rd):.0%}")
        avg = sum(float(a.get("readiness", 0)) for a in assets) / len(assets)
        msg = f"Avg readiness {avg:.0%}\n" + "\n".join(lines)
        return CopilotResponse(type="text", message=msg, source_state_id=sid)

    def _handle_decision_log(self, tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_decisions")
        if not fn:
            return CopilotResponse(type="text", message="No decision log available.", source_state_id=sid)
        rows = fn()
        if not rows:
            return CopilotResponse(type="text", message="No decisions recorded yet.", source_state_id=sid)
        msg = "\n".join(
            f"• {r.get('decision_id', '?')}: {r.get('coa_id')} @ {r.get('timestamp', '')[:19]} — {r.get('source_state_id', '')}"
            for r in rows[-8:]
        )
        return CopilotResponse(type="text", message=f"Recent decisions:\n{msg}", source_state_id=sid)

    def _handle_explain(self, args: list[str], state: dict, tools: dict, sid: str, text: str) -> CopilotResponse:
        explain_fn = tools.get("explain_coa")
        if not explain_fn:
            return CopilotResponse(type="error", message="Explanation not available.", source_state_id=sid)

        coa_id = args[0] if args else None
        question = "Why is this ranked first?"
        if text.startswith("/why"):
            rest = text[len("/why"):].strip()
            if rest and not rest.split()[0].startswith("coa-"):
                question = rest
        result = explain_fn(coa_id=coa_id, question=question)
        return CopilotResponse(
            type="explanation", message="Explanation generated.", data=result, source_state_id=sid,
            suggested_actions=["Simulate top plan", "Compare top 2"],
        )

    def _handle_simulate(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        sim_fn = tools.get("simulate_coa")
        if not sim_fn:
            return CopilotResponse(type="error", message="Simulation not available.", source_state_id=sid)

        coa_id = args[0] if args else None
        result = sim_fn(coa_id=coa_id)
        return CopilotResponse(
            type="simulation", message="Simulation complete.", data=result, source_state_id=sid,
            suggested_actions=["Approve selected plan", "Re-plan"],
        )

    def _handle_compare(self, args: list[str], state: dict, tools: dict, sid: str) -> CopilotResponse:
        compare_fn = tools.get("compare_coas")
        if not compare_fn:
            return CopilotResponse(type="error", message="Comparison not available.", source_state_id=sid)

        ids: list[str] | None
        if len(args) >= 2:
            ids = args[:2]
        elif len(args) == 1 and args[0].lower() in ("top2", "top", "2"):
            ids = None
        else:
            ids = None
        result = compare_fn(ids)
        return CopilotResponse(
            type="comparison", message="Comparison ready.", data=result, source_state_id=sid,
            suggested_actions=["Why this plan?", "Simulate top plan"],
        )

    def _handle_what_changed(self, state: dict, sid: str) -> CopilotResponse:
        events = state.get("events_log", [])
        recent = events[-5:] if events else []

        prompt = (
            f"Recent events:\n{_fmt(recent)}\n\n"
            "Summarize what changed recently for the operator."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=300)
        if not msg:
            if recent:
                lines = [f"• T+{e.get('t_s', 0):.0f}s: {e.get('summary', e.get('type', '?'))}" for e in recent]
                msg = "Recent changes:\n" + "\n".join(lines)
            else:
                msg = "No recent events recorded."

        return CopilotResponse(
            type="text", message=msg, data={"recent_events": recent}, source_state_id=sid,
        )

    def _handle_recommend(self, state: dict, tools: dict, sid: str) -> CopilotResponse:
        get_coas = tools.get("get_current_coas")
        coas = get_coas() if get_coas else []

        if not coas:
            return CopilotResponse(
                type="text",
                message="No COAs generated yet. Generate plans first to get a recommendation.",
                source_state_id=sid,
                suggested_actions=["Generate COAs"],
            )

        top = coas[0] if isinstance(coas, list) and coas else {}
        prompt = (
            f"Current COAs:\n{_fmt(coas[:3])}\n\n"
            "Recommend the best option and explain why in 2-3 sentences."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=300)
        if not msg:
            title = top.get("title", "Option A") if isinstance(top, dict) else "Option A"
            msg = f"Recommended: {title}. It offers the best balance of protection and readiness preservation."

        return CopilotResponse(
            type="text", message=msg, source_state_id=sid,
            suggested_actions=["Why this plan?", "Simulate top plan", "Approve selected plan"],
        )

    def _handle_focus(self, args: list[str], state: dict, sid: str) -> CopilotResponse:
        target = args[0] if args else ""
        return CopilotResponse(
            type="focus", message=f"Focused on {target}.",
            data={"focus_id": target}, source_state_id=sid,
        )

    def _handle_approve(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        return CopilotResponse(
            type="text",
            message="Use the Approve button on a specific COA to confirm. Operator approval is always manual.",
            source_state_id=sid,
        )

    def _handle_brief(self, state: dict, tools: dict, sid: str) -> CopilotResponse:
        summary = self._build_basic_summary(state)
        get_coas = tools.get("get_current_coas")
        coas = get_coas() if get_coas else []

        prompt = (
            f"State summary:\n{_fmt(summary)}\n"
            f"Current COAs (top 2):\n{_fmt(coas[:2])}\n\n"
            "Generate a commander's brief in plain English. "
            "Cover: situation, threat picture, current plan status, readiness, and recommended next steps. "
            "Keep it to 3-5 paragraphs."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=600)
        if not msg:
            msg = self._format_summary_fallback(summary)
            if coas:
                top_title = coas[0].get("title", "Option A") if isinstance(coas[0], dict) else "Option A"
                msg += f"\n\nTop plan: {top_title}."

        return CopilotResponse(
            type="text", message=msg, source_state_id=sid,
            suggested_actions=self._suggest_from_state(state),
        )

    def _handle_set_reserve(self, args: list[str], sid: str) -> CopilotResponse:
        val = args[0] if args else "2"
        return CopilotResponse(
            type="text",
            message=f"Reserve policy noted: keep {val} interceptor pair(s) in reserve. Apply this when generating COAs.",
            data={"reserve_pairs": val},
            source_state_id=sid,
            suggested_actions=["Generate COAs", "Re-plan"],
        )

    def _handle_set_policy(self, args: list[str], sid: str) -> CopilotResponse:
        policy = " ".join(args) if args else "default"
        return CopilotResponse(
            type="text",
            message=f"Policy set: {policy}. This will be applied to future COA generation.",
            data={"policy": policy},
            source_state_id=sid,
            suggested_actions=["Generate COAs"],
        )

    def _handle_freeform(self, text: str, state: dict, sid: str) -> CopilotResponse:
        summary = self._build_basic_summary(state)
        prompt = (
            f"Operator question: \"{text}\"\n\n"
            f"Current state:\n{_fmt(summary)}\n\n"
            "Answer the operator's question based on the current tactical situation. "
            "Be concise and direct."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            msg = (
                "I can help with tactical questions. Try commands like /summary, /top-threats, "
                "/generate-coas, or ask about specific tracks and zones."
            )
        return CopilotResponse(
            type="text", message=msg, source_state_id=sid,
            suggested_actions=self._suggest_from_state(state),
        )

    def _build_basic_summary(self, state: dict) -> dict[str, Any]:
        tracks = state.get("tracks", [])
        assets = state.get("assets", [])
        hostile_count = sum(1 for t in tracks if t.get("side") == "hostile")
        ready_assets = sum(1 for a in assets if a.get("status") in ("ready", "standby", "alert"))
        recovering = sum(1 for a in assets if a.get("status") == "recovering")
        avg_readiness = (sum(a.get("readiness", 1.0) for a in assets) / max(len(assets), 1))
        return {
            "wave": state.get("wave", 0),
            "time_s": state.get("current_time_s", 0),
            "hostile_tracks": hostile_count,
            "total_assets": len(assets),
            "ready_assets": ready_assets,
            "recovering_assets": recovering,
            "avg_readiness": round(avg_readiness, 2),
            "coa_trigger_pending": state.get("coa_trigger_pending", False),
        }

    def _format_summary_fallback(self, data: dict) -> str:
        return (
            f"Wave {data.get('wave', 0)} | T+{data.get('time_s', 0):.0f}s\n"
            f"Hostile tracks: {data.get('hostile_tracks', 0)}\n"
            f"Assets: {data.get('ready_assets', 0)} ready, {data.get('recovering_assets', 0)} recovering "
            f"(avg readiness {data.get('avg_readiness', 1.0):.0%})\n"
            f"{'COA generation recommended.' if data.get('coa_trigger_pending') else ''}"
        )

    def _suggest_from_state(self, state: dict) -> list[str]:
        actions = []
        if state.get("coa_trigger_pending"):
            actions.append("Generate COAs")
        if state.get("wave", 0) >= 2:
            actions.append("Re-plan")
        return actions


def _fmt(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj, indent=2, default=str)[:3000]
    except Exception:
        return str(obj)[:3000]
