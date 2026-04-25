# AGENTS.md — LJFC COMMAND v0.4

## Mission
Build LJFC COMMAND, a surveillance-led, AI-assisted air-defence planning and decision-support prototype for the Saab  hackathon.

## Product boundary
1. This is a planning, rehearsal, and simulation product.
2. It is not a live combat-control or fire-control product.
3. It does not automate lethal decisions.
4. All capabilities, rules, and performance values remain synthetic and non-classified.
5. Human approval is required before any recommended plan is considered chosen.

## Canonical demo truth
- Primary scenario: `scenario_alpha` / Two-Wave Pressure Test
- Primary UI: one visible Unified Copilot
- Primary map approach: SVG/Canvas tactical display on a fictional local-km grid
- Primary fallback: `mock` mode with deterministic fixtures
- Primary visual identity: neon green on black

## Research-review takeaway
Treat the external research review as validation plus a few clarifications:
- stronger event lineage,
- stronger planner guardrails,
- stronger UI token contract,
- future adapter placeholders.

Do not widen the MVP because of it.

## User-facing language rules
- Say Unified Copilot, not “PlannerAgent”, “ExplainerAgent”, etc.
- Say recommended plan or course of action, not “autonomous response”.
- Say approve plan, not “execute strike”.
- Say simulation-backed and human-in-the-loop often enough that the intent is obvious.

## Internal architecture rules
Internally you may decompose the system into modules for:
- situation assessment,
- threat scoring,
- planning,
- explanation,
- simulation,
- data generation,
- audit/replay,
- future adapter stubs.

Those modules are implementation details. The user sees one copilot.

## Required runtime contracts
Keep these files explicit and visible:
- `scoring_params.json`
- `policy_profiles.json`
- `effector_suitability.json`
- `planning_guardrails.json`
- `event_taxonomy.json`
- output schemas in `/schemas`

## Data invariants
- Use the Boreal Passage JSON pack as the canonical runtime dataset.
- Treat coordinates as a fictional local grid, not real geospatial coordinates.
- Prefer JSON contract files over implicit assumptions.
- Keep scenario playback deterministic.
- Preserve snapshot IDs for explanation, comparison, simulation, and audit.

## Planning invariants
- Always support a balanced mix of fighters/interceptors, ground-based air defence, and UAV/support assets.
- Keep reserve/QRA posture explicit.
- Surface policy profile and assumptions in every COA.
- Use the same policy and suitability logic for planning and explanation.
- Reject or flag impossible COAs.
- Default guardrail: do not recommend committing more than 75% of currently available force unless:
  - policy overrides it,
  - the threat is explicitly treated as existential,
  - or the operator clearly accepts the override.

## Explanation invariants
Every recommendation or explanation should reference concrete objects when possible:
- `track_id`
- `asset_id`
- `zone_id`
- selected policy profile
- reserve posture
- assumptions / uncertainty notes
- `source_state_id` when relevant

Do not produce vague “AI says so” reasoning.
Default explanation style: direct, factual, concise, low-hedge.

## Simulation invariants
- Deterministic seed support is required.
- Simulation output must be serializable.
- Outcomes should include readiness remaining.
- Simulation results must preserve `source_state_id`.
- The simulator may be simple, but it must be explainable and reproducible.

## UI invariants
- Black or near-black surfaces
- Neon green primary text and linework
- Map centered
- Left rail for alerts
- Right rail for Unified Copilot and plan detail
- Bottom bar for timeline / event log
- Avoid generic dark-blue AI dashboard styling
- Avoid clutter, sci-fi parody, or hard-to-read glow effects
- The explanation path should be reachable within two interactions
- Use explicit theme tokens rather than ad hoc colours

## Engineering rules
- Prefer small, testable modules.
- Prefer strict typing.
- Prefer schema-first interfaces.
- Keep online LLM optional.
- `mock` mode must always stay usable.
- Never hard-code secrets.
- Never commit API keys.
- Clear context between separate AI coding tasks.
- Preserve stable requirement IDs or contract names where possible.

## Supported LLM modes
- `mock`
- `openrouter`
- `google`
- `ollama`

Default assumption for the demo path: `mock` must work even if every online call fails.

## Future integration rule
If you add sensor/effector/comms adapters, keep them as mock-only interfaces or docs.
Do not add live integrations into the MVP path.

## Task handoff format for AI coding tools
For each task, include:
1. Objective
2. Files allowed to change
3. Files forbidden to change
4. Required contracts or schemas
5. Acceptance tests
6. Expected output shape
7. Risks or follow-up notes

## Definition of done
A task is done only if:
- the requested feature works,
- touched types/tests pass,
- schema-bound outputs validate,
- the UI still respects the neon tactical design,
- the change improves or preserves the golden-path demo,
- the feature still works in `mock` mode unless explicitly marked otherwise,
- snapshot lineage is not broken for core flows.

## Preferred repository layout
/apps/web  
/apps/api  
/packages/domain  
/packages/scenario-data  
/packages/simulation  
/packages/ui  
/packages/contracts  
/packages/adapters  
/prompts  
/schemas  
/docs
