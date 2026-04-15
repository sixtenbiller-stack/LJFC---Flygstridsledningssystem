# NEON COMMAND v0.4 — Research Alignment Memo
## Review of Claude/Gemini research input vs current NEON COMMAND direction

Version: 0.4  
Date: 2026-04-14

---

## Bottom line

The research packet is mostly a **confirmation document**, not a direction-changing document.

It strongly reinforces the direction already taken:
- ontology-first state,
- simulation-backed COAs,
- one visible Unified Copilot,
- human-in-the-loop approval,
- a narrow two-wave jury demo,
- neon-green-on-black tactical ergonomics,
- mock-safe deterministic fallback.

Because of that, v0.4 does **not** broaden the product or replace the existing concept.

---

## What the research adds that is genuinely useful

### 1. Stronger event and snapshot lineage
The research is helpful in making it explicit that:
- every recommendation,
- every simulation run,
- and every approved decision

should point back to the exact state snapshot that produced it.

That makes the audit story much stronger.

### 2. Stronger planner guardrails
The research gives a good concrete planning heuristic:
- avoid committing more than 75% of currently available force unless the threat is existential or a policy override is explicit.

That is useful because it gives Cursor/Codex-style tools a clearer planning rule to implement.

### 3. Stronger UI token contract
The research usefully re-emphasizes:
- off-black rather than pure black,
- explicit neon-green / amber / red / neutral tokens,
- the rigid left / center / right / bottom layout,
- explanation accessible within two interactions.

That is good implementation guidance, not just style preference.

### 4. Better product-story framing
The research helps the pitch:
- surveillance fusion,
- cognitive overload relief,
- reserve-aware decision support,
- forward-deployed engineering / fast operator-centric build style.

That is more helpful for presentation than for changing the build.

### 5. Useful future integration placeholders
The research is helpful in showing what future interface points could exist:
- sensor update adapters,
- track-fusion adapters,
- effector preview adapters,
- comms resilience adapters.

These are product-story placeholders only. They should not expand the hackathon build.

---

## What did not change

These points remain unchanged and should stay unchanged:

- Canonical scenario: `scenario_alpha`
- One visible AI: Unified Copilot
- Tactical map default: SVG/Canvas, local grid
- Demo posture: mock-first, deterministic
- Product boundary: planning and decision support, not live combat execution
- Build strategy: one polished slice for the jury

---

## Why scope should stay narrow

The official hackathon guidance is still the governing constraint:
- show a mission-critical workflow,
- show that your solution helps users succeed much better,
- focus on one of the most interesting parts of the full solution,
- do not try to build the whole thing.

So the research should improve precision, not encourage feature sprawl.

---

## Concrete v0.4 deltas made because of the research

1. Added `planning_guardrails.json`
2. Added `event_taxonomy.json`
3. Strengthened `source_state_id` / snapshot lineage requirements
4. Added explicit default theme tokens
5. Added explicit explanation-style guidance: direct, factual, low-hedge
6. Added future adapter placeholders as P1 / post-demo only

---

## Recommendation to the team

Use the research mainly in two places:

### In the build
- implement the guardrails,
- implement snapshot-linked outputs,
- implement the explicit UI token set,
- keep the rest of the MVP narrow.

### In the pitch
- use the research language to justify why this matters:
  - faster OODA-loop support,
  - lower cognitive burden,
  - explainable AI,
  - reserve-aware planning,
  - deterministic simulation and fallback.

That is the highest-value way to use it.
