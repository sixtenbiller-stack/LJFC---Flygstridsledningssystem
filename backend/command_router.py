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
    # Scenario / mode commands
    "/scenario": "scenario_info",
    "/mode": "scenario_info",
    "/live-status": "live_status",
    "/mutations": "live_status",
    "/jump": "jump_to",
    # Group-aware commands
    "/groups": "list_groups",
    "/group": "show_group",
    "/most-dangerous-group": "show_group",
    "/assess": "assess_group",
    "/why-group": "explain_group",
    "/uncertainty": "uncertainty_group",
    "/responses": "list_responses",
    "/why-response": "explain_response",
    "/compare-responses": "compare_responses",
    "/simulate-response": "simulate_coa",
    "/generate-detailed-coas": "generate_coas",
    "/authority": "authority_check",
    "/defer": "defer_group",
    "/override": "override_group",
    "/after-action": "after_action",
}

NL_INTENTS = [
    (r"(?:what|which)\s+(?:changed|happened|is new)", "what_changed"),
    (r"(?:which|what)\s+(?:is\s+the\s+)?most\s+dangerous\s+(?:coordinated\s+)?(?:group|threat)", "show_group"),
    (r"(?:which|what)\s+threat.*(?:most|greatest|biggest|worst)", "top_threats"),
    (r"(?:why|how).*(?:system|ai)\s+(?:think|classify|group|cluster).*(?:swarm|coordinated|group)", "explain_group"),
    (r"(?:what\s+happens?\s+if\s+(?:we\s+)?do\s+nothing|inaction|if\s+nothing)", "inaction"),
    (r"(?:best|top|admissible)\s+(?:response|option|action).*(?:readiness|current)", "list_responses"),
    (r"(?:who|authority|approve).*(?:can\s+approve|right\s+now|authorized)", "authority_check"),
    (r"(?:fast|slow)\s+lane|why\s+(?:is\s+this|was\s+this)\s+(?:in\s+)?(?:fast|slow)", "explain_group"),
    (r"(?:after.?action|replay|review\s+last)", "after_action"),
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
    (r"(?:group|cluster|coordinated)", "list_groups"),
    (r"(?:what\s+scenario|which\s+scenario|scenario\s+loaded)", "scenario_info"),
    (r"(?:replay|live)\s+mode|are\s+we\s+in\s+(?:replay|live)", "scenario_info"),
    (r"(?:take\s+me\s+to|jump\s+to|go\s+to)\s+(?:the\s+)?(?:first\s+)?(contact|group|decision|second\s+wave)", "jump_to"),
    (r"(?:what\s+seed|seed\s+generated|generated\s+from)", "scenario_info"),
    (r"(?:what\s+is\s+the\s+)?(?:current\s+)?state\s+id", "state_id"),
    (r"(?:what\s+changed\s+since|last\s+mutation|mutation\s+log)", "live_status"),
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
        elif intent == "list_groups":
            return self._handle_list_groups(tools, source_state_id)
        elif intent == "show_group":
            return self._handle_show_group(args, tools, source_state_id)
        elif intent == "assess_group":
            return self._handle_show_group(args, tools, source_state_id)
        elif intent == "explain_group":
            return self._handle_explain_group(args, tools, state_summary, source_state_id, text)
        elif intent == "uncertainty_group":
            return self._handle_uncertainty(args, tools, source_state_id)
        elif intent == "list_responses":
            return self._handle_list_responses(args, tools, source_state_id)
        elif intent == "explain_response":
            return self._handle_explain_response(args, tools, state_summary, source_state_id)
        elif intent == "compare_responses":
            return self._handle_compare_responses(args, tools, source_state_id)
        elif intent == "authority_check":
            return self._handle_authority(args, tools, source_state_id)
        elif intent == "defer_group":
            return self._handle_defer(args, source_state_id)
        elif intent == "override_group":
            return self._handle_override(args, source_state_id)
        elif intent == "after_action":
            return self._handle_after_action(tools, source_state_id)
        elif intent == "inaction":
            return self._handle_inaction(args, tools, source_state_id)
        elif intent == "scenario_info":
            return self._handle_scenario_info(state_summary, tools, source_state_id)
        elif intent == "live_status":
            return self._handle_live_status(tools, source_state_id)
        elif intent == "jump_to":
            return self._handle_jump(args, tools, source_state_id)
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
            "• Scenario: /scenario /mode /live-status /mutations\n"
            "• Navigation: /jump first-contact | first-group | first-decision | second-wave\n"
            "• Groups: /groups /group top /most-dangerous-group /assess top /why-group top /uncertainty top\n"
            "• Responses: /responses top /why-response top /compare-responses top\n"
            "• Planning: /generate-coas /generate-detailed-coas top /recommend /replan\n"
            "• Explain/Compare: /why top | /compare (top2)\n"
            "• Simulation: /simulate top | /simulate-response top\n"
            "• Authority: /authority top\n"
            "• Policy: /policy <name> /reserve <n>\n"
            "• Decision: /approve top /defer top /override top\n"
            "• Audit: /decision-log /after-action /state-id\n"
            "• Focus: /focus <id>\n"
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

    # ── Group-aware handlers ──

    def _handle_list_groups(self, tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_groups")
        groups = fn() if fn else []
        if not groups:
            return CopilotResponse(type="text", message="No threat groups formed yet. Start playback and wait for threats.", source_state_id=sid)
        lines = []
        for g in groups:
            lane = g.get("recommended_lane", "?").upper()
            gt = g.get("group_type", "?").replace("_", " ")
            n = len(g.get("member_track_ids", []))
            urg = g.get("urgency_score", 0)
            lines.append(f"• {g['group_id']}: {gt} — {n} tracks, urgency {urg:.0%}, {lane} lane")
        msg = f"{len(groups)} threat group(s):\n" + "\n".join(lines)
        return CopilotResponse(type="groups", message=msg, data={"groups": groups}, source_state_id=sid,
                               suggested_actions=["Show top group", "Responses for top group"])

    def _handle_show_group(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_group")
        if not fn:
            return CopilotResponse(type="error", message="Group data not available.", source_state_id=sid)
        gid = args[0] if args else None
        g = fn(group_id=gid)
        if "error" in g:
            return CopilotResponse(type="error", message=g["error"], source_state_id=sid)

        prompt = (
            f"Threat group assessment:\n{_fmt(g)}\n\n"
            "Summarize this threat group for the operator: what it is, why the system classified it this way, "
            "what is most at risk, urgency, confidence, and recommended lane."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            msg = g.get("short_narration", "No narration available.")
            if g.get("rationale"):
                msg += "\n\nAssessment:\n" + "\n".join(f"• {r}" for r in g["rationale"])
        return CopilotResponse(type="group_detail", message=msg, data={"group": g}, source_state_id=sid,
                               suggested_actions=["Show responses", "What if we do nothing?", "Generate detailed COAs"])

    def _handle_explain_group(self, args: list[str], tools: dict, state: dict, sid: str, text: str) -> CopilotResponse:
        fn = tools.get("get_group")
        if not fn:
            return CopilotResponse(type="error", message="Group data not available.", source_state_id=sid)
        gid = args[0] if args else None
        g = fn(group_id=gid)
        if "error" in g:
            return CopilotResponse(type="error", message=g["error"], source_state_id=sid)

        prompt = (
            f"Operator question: \"{text}\"\n\n"
            f"Threat group data:\n{_fmt(g)}\n\n"
            "Answer why this group was classified this way. Reference coordination score, member tracks, "
            "heading alignment, timing, and uncertainty flags."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            ev = g.get("evidence", [])
            lines = [f"• {e.get('factor', '?')}: {e.get('value', 0)} — {e.get('detail', '')}" for e in ev]
            msg = f"Group {g.get('group_id', '?')} classification evidence:\n" + "\n".join(lines) if lines else "No evidence detail available."
        return CopilotResponse(type="text", message=msg, data={"group": g}, source_state_id=sid)

    def _handle_uncertainty(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_group")
        if not fn:
            return CopilotResponse(type="error", message="Group data not available.", source_state_id=sid)
        gid = args[0] if args else None
        g = fn(group_id=gid)
        if "error" in g:
            return CopilotResponse(type="error", message=g["error"], source_state_id=sid)
        flags = g.get("uncertainty_flags", [])
        if not flags:
            msg = f"No uncertainty flags on {g.get('group_id', '?')}. Confidence: {g.get('confidence', 0):.0%}."
        else:
            lines = [f"• [{f.get('severity', '?').upper()}] {f.get('flag', '?')}: {f.get('detail', '')}" for f in flags]
            msg = f"Uncertainty for {g.get('group_id', '?')} (confidence {g.get('confidence', 0):.0%}):\n" + "\n".join(lines)
        return CopilotResponse(type="text", message=msg, data={"group": g}, source_state_id=sid)

    def _handle_list_responses(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_responses")
        if not fn:
            return CopilotResponse(type="error", message="Response ranking not available.", source_state_id=sid)
        gid = args[0] if args else None
        responses = fn(group_id=gid)
        if not responses:
            return CopilotResponse(type="text", message="No responses ranked yet.", source_state_id=sid)
        lines = []
        for r in responses[:5]:
            lines.append(f"#{r.get('rank', '?')} {r.get('title', '?')} — effectiveness {r.get('expected_effectiveness', 0):.0%}, cost {r.get('readiness_cost_pct', 0):.0f}%")
        msg = f"Top {len(lines)} response options:\n" + "\n".join(lines)
        return CopilotResponse(type="responses", message=msg, data={"responses": responses}, source_state_id=sid,
                               suggested_actions=["Why top response?", "Compare responses", "Approve top"])

    def _handle_explain_response(self, args: list[str], tools: dict, state: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_responses")
        if not fn:
            return CopilotResponse(type="error", message="Response data not available.", source_state_id=sid)
        gid = args[0] if args else None
        responses = fn(group_id=gid)
        if not responses:
            return CopilotResponse(type="text", message="No responses available.", source_state_id=sid)
        top = responses[0]
        prompt = (
            f"Top response option:\n{_fmt(top)}\n\n"
            "Explain why this is the recommended response. Reference effectiveness, cost, authority, and trade-offs."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            rationale = top.get("rationale", [])
            msg = f"Recommended: {top.get('title', '?')}\n" + "\n".join(f"• {r}" for r in rationale) if rationale else f"Recommended: {top.get('title', '?')}"
        return CopilotResponse(type="text", message=msg, data={"response": top}, source_state_id=sid,
                               suggested_actions=["Approve top", "Simulate top", "Compare responses"])

    def _handle_compare_responses(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_responses")
        if not fn:
            return CopilotResponse(type="error", message="Response data not available.", source_state_id=sid)
        gid = args[0] if args else None
        responses = fn(group_id=gid)
        if len(responses) < 2:
            return CopilotResponse(type="text", message="Need at least 2 responses to compare.", source_state_id=sid)
        a, b = responses[0], responses[1]
        prompt = (
            f"Option A:\n{_fmt(a)}\n\nOption B:\n{_fmt(b)}\n\n"
            "Compare these two response options. Highlight key trade-offs in effectiveness, cost, reversibility, and authority."
        )
        msg = gemini_provider.generate(prompt, system_instruction=SYSTEM_INSTRUCTION, max_tokens=400)
        if not msg:
            msg = (f"#{a.get('rank')}: {a.get('title')} — {a.get('expected_effectiveness', 0):.0%} effective, "
                   f"{a.get('readiness_cost_pct', 0):.0f}% cost, {a.get('reversibility', '?')} reversibility\n"
                   f"#{b.get('rank')}: {b.get('title')} — {b.get('expected_effectiveness', 0):.0%} effective, "
                   f"{b.get('readiness_cost_pct', 0):.0f}% cost, {b.get('reversibility', '?')} reversibility")
        return CopilotResponse(type="comparison", message=msg, data={"responses": [a, b]}, source_state_id=sid)

    def _handle_authority(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_decision_card")
        if not fn:
            return CopilotResponse(type="text", message="No decision card available.", source_state_id=sid)
        gid = args[0] if args else None
        card = fn(group_id=gid)
        if "error" in card:
            return CopilotResponse(type="text", message=card["error"], source_state_id=sid)
        rec = card.get("recommended_response", {})
        auth = rec.get("authority_required", "unknown")
        trust = card.get("data_trust_level", "unknown")
        msg = (f"Authority status: {auth.replace('_', ' ').upper()}\n"
               f"Data trust level: {trust.upper()}\n"
               f"Top response: {rec.get('title', '?')}")
        if auth == "needs_confirmation":
            msg += "\n\n⚠ This response requires confirmation from higher command before execution."
        elif auth == "policy_blocked":
            msg += "\n\n⛔ Current policy blocks this response. Override or select an alternative."
        return CopilotResponse(type="text", message=msg, data={"decision_card": card}, source_state_id=sid)

    def _handle_defer(self, args: list[str], sid: str) -> CopilotResponse:
        gid = args[0] if args else "top"
        return CopilotResponse(
            type="text",
            message=f"Decision deferred for {gid}. Group will continue to be monitored. Use /groups to revisit.",
            source_state_id=sid,
            suggested_actions=["Show groups", "What changed?"],
        )

    def _handle_override(self, args: list[str], sid: str) -> CopilotResponse:
        return CopilotResponse(
            type="text",
            message="To override: use the Decision Card and select 'Override with reason'. This will be logged in the after-action record.",
            source_state_id=sid,
        )

    def _handle_after_action(self, tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_after_action")
        records = fn() if fn else []
        if not records:
            return CopilotResponse(type="text", message="No after-action records yet.", source_state_id=sid)
        lines = []
        for r in records[-5:]:
            lines.append(f"• {r.get('record_id', '?')}: {r.get('operator_action', '?')} {r.get('response_family', '?')} "
                         f"for {r.get('group_id', '?')} (wave {r.get('wave', '?')})")
        msg = "After-action log:\n" + "\n".join(lines)
        return CopilotResponse(type="text", message=msg, data={"records": records}, source_state_id=sid)

    def _handle_inaction(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_group")
        if not fn:
            return CopilotResponse(type="text", message="No group data available.", source_state_id=sid)
        gid = args[0] if args else None
        g = fn(group_id=gid)
        if "error" in g:
            return CopilotResponse(type="text", message=g["error"], source_state_id=sid)
        consequence = g.get("inaction_consequence", "No inaction assessment available.")
        msg = f"If nothing is done:\n{consequence}"
        return CopilotResponse(type="text", message=msg, data={"group": g}, source_state_id=sid,
                               suggested_actions=["Show responses", "Approve top response"])

    def _handle_scenario_info(self, state: dict, tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_session_info")
        session = fn() if fn else {}
        if not session:
            rmode = state.get("runtime_mode", state.get("mode", "replay"))
            name = state.get("scenario_name", state.get("scenario_id", "Unknown"))
            msg = f"Active scenario: **{name}**\nMode: {rmode.upper()}\nState ID: {sid}"
        else:
            name = session.get("scenario_label", session.get("scenario_id", "Unknown"))
            rmode = session.get("runtime_mode", "replay")
            origin = session.get("scenario_origin", "builtin")
            lines = [
                f"**{name}**",
                f"Mode: {rmode.upper()} · Origin: {origin.upper().replace('_', ' ')}",
                f"State ID: {sid}",
            ]
            if session.get("template_name"):
                lines.append(f"Template: {session['template_name']}")
            if session.get("seed") is not None:
                lines.append(f"Seed: {session['seed']}")
            if session.get("runtime_session_id"):
                lines.append(f"Session: {session['runtime_session_id']}")
            if session.get("source_parent_scenario"):
                lines.append(f"Source: {session['source_parent_scenario']}")
            lines.append(f"Tracks: {session.get('track_count', '?')} | Groups: {session.get('group_count', '?')}")
            if session.get("extended_schema_present"):
                lines.append("Extended fields: present")
            if session.get("description"):
                lines.append(f"_{session['description']}_")
            msg = "\n".join(lines)
        return CopilotResponse(type="text", message=msg, data=session, source_state_id=sid,
                               suggested_actions=["/groups", "/brief", "/jump first-contact"])

    def _handle_live_status(self, tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("get_session_info")
        session = fn() if fn else {}
        if session.get("runtime_mode") != "live":
            return CopilotResponse(type="text", message="Not in live mode. Use Scenario Lab to start a live session.",
                                   source_state_id=sid)
        lines = [
            f"**Live session active**",
            f"Session: {session.get('runtime_session_id', '?')}",
            f"Source: {session.get('source_parent_scenario', '?')}",
            f"Time: {session.get('current_time_s', '?')}s",
            f"Tracks: {session.get('track_count', '?')} | Groups: {session.get('group_count', '?')}",
        ]
        count = session.get("last_mutation_count", 0)
        lines.append(f"Total mutations: {count}")
        mlog = session.get("mutation_log", [])
        if mlog:
            lines.append("Recent:")
            for m in mlog[-5:]:
                lines.append(f"  • {m.get('type','?')} at t={m.get('t_s','?')}s")
        return CopilotResponse(type="text", message="\n".join(lines), data=session, source_state_id=sid,
                               suggested_actions=["/groups", "/brief"])

    def _handle_jump(self, args: list[str], tools: dict, sid: str) -> CopilotResponse:
        fn = tools.get("jump_to")
        if not fn:
            return CopilotResponse(type="text", message="Jump not available.", source_state_id=sid)
        target_map = {
            "first-contact": "first_contact", "contact": "first_contact",
            "first-group": "first_group", "group": "first_group",
            "first-decision": "first_decision", "decision": "first_decision",
            "second-wave": "second_wave", "wave": "second_wave", "second": "second_wave",
        }
        raw = "-".join(args).lower() if args else "first-contact"
        target = target_map.get(raw, raw.replace("-", "_"))
        result = fn(target)
        if "error" in result:
            return CopilotResponse(type="text", message=result["error"], source_state_id=sid)
        msg = f"Jumped to **{result.get('label', target)}** at {result.get('time_s', '?')}s. {result.get('tracks_at_target', 0)} tracks visible."
        return CopilotResponse(type="text", message=msg, data=result, source_state_id=sid,
                               suggested_actions=["/groups", "/brief", "/top-threats"])

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
