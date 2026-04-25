# LJFC COMMAND v0.4 — Execution Backlog
## Cursor / Codex / Claude Code / Gemini / AI-Tool Build Plan
Version: 0.4  
Status: updated after review of the research memo and kick-off guidance

---

## 1. Execution strategy

This backlog is optimized for:
- one polished jury demo,
- low integration risk,
- small AI-tool-friendly tasks,
- deterministic local execution,
- a single visible Unified Copilot,
- one canonical scenario: `scenario_alpha`.

### Operating rules
1. Build the golden path first.
2. Default to mock data before online LLM calls.
3. Keep tasks file-bounded and testable.
4. Use SVG/Canvas for the tactical map by default.
5. Do not split the visible UI into multiple named agents.
6. Do not widen scope because of future-integration ideas.
7. Treat research-driven additions as clarifications, not a license to build more surface area.

---

## 2. Parallel work lanes

### Lane A — Data, contracts, and state
Owner focus:
- contracts,
- Boreal Passage data pack,
- playback,
- snapshots,
- threat scoring,
- readiness,
- event taxonomy.

### Lane B — Tactical UI
Owner focus:
- neon theme,
- design tokens,
- SVG/Canvas tactical map,
- alert queue,
- scorecards,
- explanation drawer,
- timeline,
- polish.

### Lane C — Copilot, planning, and simulation
Owner focus:
- structured COA pipeline,
- mock/live LLM routing,
- planner guardrails,
- explanation flow,
- simulation engine,
- re-plan flow,
- approval receipt.

---

## 3. Ticket list

## T00 — Repo skeleton and startup path (P0)
### Goal
Create a clean repo that starts locally and supports parallel work.

### Acceptance
- repo layout matches the v0.4 spec,
- `.env.example` exists,
- one documented startup command exists,
- `mock` mode works without secrets,
- README explains `mock`, `openrouter`, `google`, and `ollama`.

### Allowed files
- workspace config
- package manifests
- starter app folders
- README
- `.env.example`

### AI task card
> Objective: scaffold the LJFC COMMAND repo for a local-first jury demo.  
> Allowed files: workspace config, package manifests, starter folders, README, env example.  
> Forbidden: business logic, UI feature implementation, simulation logic.  
> Requirements: one command startup, mock mode documented, modular app/package layout.  
> Deliver: changed files, startup command, open risks.

---

## T01 — Contracts, event taxonomy, and shared domain types (P0)
### Goal
Lock down schemas before feature coding.

### Acceptance
- shared types exist for Track, Asset, Zone, Alert, COA, SimulationResult, AuditRecord, ScenarioEvent, StateSnapshot,
- JSON schemas exist for COA, explanation, simulation result, state snapshot, and audit record,
- `event_taxonomy.json` exists,
- type validation helpers exist.

### Allowed files
- `packages/domain/**`
- `packages/contracts/**`
- `schemas/**`
- `data/boreal_passage/event_taxonomy.json`

### AI task card
> Objective: implement shared domain types and schema contracts for the canonical demo flow.  
> Allowed files: domain, contracts, schemas, event taxonomy.  
> Forbidden: UI screens, live LLM calls.  
> Requirements: strict typing, schema alignment, source snapshot lineage support, example fixtures.  
> Done when: frontend and backend can import the same contracts and every core output can reference a snapshot.

---

## T02 — Boreal Passage normalization and validation (P0)
### Goal
Make the uploaded data pack the canonical runtime dataset.

### Acceptance
- loaders exist for `geography.json`, `assets.json`, `scoring_params.json`, `policy_profiles.json`, `effector_suitability.json`, `planning_guardrails.json`, and `scenario_alpha.json`,
- mock-response fixtures are loadable by ID,
- validation produces readable errors,
- helper returns a full scenario bundle.

### Allowed files
- `packages/scenario-data/**`
- `data/boreal_passage/**`
- validation scripts

### AI task card
> Objective: normalize and validate the Boreal Passage runtime pack.  
> Allowed files: scenario-data package, data files, validation scripts.  
> Forbidden: UI logic, copilot logic.  
> Requirements: local-only, deterministic, readable validation failures, fixture lookup helpers.  
> Deliver: loader, validator, example bundle output.

---

## T03 — Scenario engine, snapshots, and cue points (P0)
### Goal
Drive the app from a replayable event timeline.

### Acceptance
- scenario engine supports play, pause, seek, and speed,
- state snapshots can be frozen at any event time,
- cue points exist for wave 1, COA request, simulation moment, wave 2, re-plan, approval,
- engine can emit typed updates to UI and services.

### Allowed files
- `apps/api/src/scenario/**` or equivalent
- `packages/domain/**`

### AI task card
> Objective: implement a deterministic scenario playback engine for `scenario_alpha`.  
> Allowed files: scenario engine, state store, event selectors, tests.  
> Forbidden: frontend rendering, LLM integration.  
> Requirements: replayable state, cue points, frozen snapshots for simulation and explanation, typed event taxonomy.  
> Done when: another service can request `current_state()` and `snapshot_at(t)`.

---

## T04 — Tactical map shell and theme tokens (P0)
### Goal
Get a striking map-centered UI working early.

### Acceptance
- Boreal Passage renders on a local-km grid,
- terrain, zones, bases, cities, SAMs, sensors, and tracks display cleanly,
- selected object panel works,
- neon-green-on-black design is visible,
- theme tokens reflect the v0.4 palette.

### Allowed files
- `apps/web/src/features/map/**`
- `packages/ui/**`
- shared map helpers
- theme token files

### AI task card
> Objective: build the tactical map shell using SVG or Canvas and implement the theme token contract.  
> Allowed files: map feature, UI tokens, selection state, map helpers.  
> Forbidden: backend services, copilot logic.  
> Requirements: premium tactical look, fast rendering, local grid coordinates, selected object drawer, explicit token file.  
> Deliver: working map shell with static sample data.

---

## T05 — Timeline, event log, and alert queue (P0)
### Goal
Make the scenario feel alive and operator-oriented.

### Acceptance
- bottom bar supports play/pause/speed/scrub,
- event log updates with scenario playback,
- alert queue renders prioritized threats,
- selecting an alert focuses the map.

### Allowed files
- `apps/web/src/features/timeline/**`
- `apps/web/src/features/alerts/**`
- `apps/web/src/state/**`

### AI task card
> Objective: build timeline controls and the alert queue.  
> Allowed files: timeline, alerts, state, event log, focus handlers.  
> Forbidden: LLM integration, simulation engine internals.  
> Requirements: deterministic playback, clean state transitions, low-latency UI updates.  
> Done when: the left and bottom rails make the demo understandable before AI is added.

---

## T06 — Threat scorer, provenance, and uncertainty view (P0)
### Goal
Turn raw track events into explainable operator attention.

### Acceptance
- threat score uses weighted factors from `scoring_params.json`,
- default weights match the v0.4 baseline unless deliberately changed,
- structured explanation factors are returned,
- track detail shows sensor provenance and confidence,
- tests cover at least 3 track patterns.

### Allowed files
- scoring service
- domain selectors
- track detail UI
- tests

### AI task card
> Objective: implement deterministic threat scoring with explainable factors.  
> Allowed files: threat scoring logic, domain selectors, relevant UI detail panels, tests.  
> Forbidden: COA generation, simulation engine.  
> Requirements: no real-world weapons assumptions, readable score decomposition, confidence/provenance visible.  
> Deliver: score formula, explanation fields, unit tests.

---

## T07 — Asset readiness, policy profiles, suitability matrix, and planner guardrails (P0)
### Goal
Make planning grounded instead of purely textual.

### Acceptance
- asset registry shows readiness, recovery, reserve state, and status,
- `policy_profiles.json`, `effector_suitability.json`, and `planning_guardrails.json` exist and are loadable,
- policy profile can be selected or passed to planning,
- reserve/QRA posture is visible in UI,
- the default overcommit guardrail is represented in logic or UI.

### Allowed files
- readiness service
- asset panel UI
- data rules files
- shared selectors

### AI task card
> Objective: implement the friendly asset model plus policy, suitability, and guardrail rule loading.  
> Allowed files: readiness services, asset panels, policy files, selectors.  
> Forbidden: chat UI, simulation engine internals.  
> Requirements: synthetic values only, reserve posture explicit, same rules available to planner and explainer, default 75% overcommit guardrail surfaced.  
> Done when: a COA can be evaluated against visible policy and suitability rules.

---

## T08 — COA schema, mock loader, and scorecard UI (P0)
### Goal
Render compelling plans before live LLM integration is attempted.

### Acceptance
- COA card UI consumes the schema,
- scorecard compares at least 2 COAs,
- mock COA responses load for wave 1 and wave 2,
- UI shows assets, objectives, readiness cost, reserve posture, assumptions, risk,
- the scorecard can flag overcommit or reserve violations.

### Allowed files
- `apps/web/src/features/plans/**`
- schema-bound model adapters
- mock response loaders

### AI task card
> Objective: build the COA cards and side-by-side scorecard using mock responses first.  
> Allowed files: plan UI, adapters, mock loaders, schema glue.  
> Forbidden: backend live agent calls if not needed.  
> Requirements: visually strong, easy to compare, clearly shows reserve and readiness, guardrail visibility.  
> Deliver: screenshotable side-by-side plan comparison.

---

## T09 — Unified Copilot service and panel (P0)
### Goal
Wrap structured planning in one clean operator-facing AI experience.

### Acceptance
- right-side panel is labeled Unified Copilot,
- actions exist for summarize, generate COAs, explain, simulate, re-plan,
- service supports modes `mock|openrouter|google|ollama`,
- live mode is optional; mock mode is stable,
- the same panel can render snapshot-linked outputs.

### Allowed files
- copilot service
- provider routing
- copilot UI
- prompt templates

### AI task card
> Objective: implement Unified Copilot as one operator-facing assistant with pluggable providers.  
> Allowed files: copilot service, provider adapters, copilot panel, prompt templates.  
> Forbidden: exposing multiple agent personas in UI, hard-coded secrets.  
> Requirements: structured outputs, mock-first operation, concise operator language, snapshot IDs preserved where relevant.  
> Done when: the same UI works with mock fixtures and optionally live LLM responses.

---

## T10 — Explanation flow with grounded citations (P0)
### Goal
Make the recommendation credible and differentiating.

### Acceptance
- operator can ask “why is Option X ranked first?”,
- explanation cites tracks, assets, policy, or reserve trade-offs,
- explanation drawer is reachable in one click from a COA card,
- explanation style is direct and factual,
- mock explanation works even when live LLM is disabled.

### Allowed files
- explanation service
- explanation drawer UI
- prompt templates
- tests or fixture adapters

### AI task card
> Objective: implement grounded explanation flow for ranked COAs.  
> Allowed files: explanation service, explanation drawer, fixtures, prompt templates.  
> Forbidden: simulation engine changes unless strictly needed.  
> Requirements: direct, factual, operator-friendly, references concrete IDs and trade-offs, avoid vague hedging.  
> Deliver: working “Why this plan?” drawer.

---

## T11 — Deterministic simulation engine and comparison view (P0)
### Goal
Validate recommendations rather than merely presenting them.

### Acceptance
- selected COA can be simulated from a frozen state,
- fixed seed produces repeatable output,
- outcome metrics and timeline events are returned,
- comparison view renders simulation outcomes for at least 2 COAs,
- simulation output preserves `source_state_id`.

### Allowed files
- `packages/simulation/**`
- simulation API
- comparison UI
- tests

### AI task card
> Objective: implement the deterministic what-if simulator for the jury demo.  
> Allowed files: simulation package, endpoints, comparison UI, tests.  
> Forbidden: real-world performance modelling, live geospatial dependencies.  
> Requirements: seeded runs, readable event timeline, outcome score, readiness remaining, snapshot lineage.  
> Done when: the demo can show “recommendation + validation”.

---

## T12 — Re-plan flow and constraint mutation (P0)
### Goal
Show thinking ahead, not just first response.

### Acceptance
- second-wave cue or changed constraint triggers re-plan,
- unavailable assets or preserved QRA rule affects COA output,
- operator can regenerate plans after a changed rule,
- updated COAs replace or compare against old ones.

### Allowed files
- copilot/planner service
- scenario integration
- plan state management
- relevant UI actions

### AI task card
> Objective: implement re-planning after second-wave detection or changed constraints.  
> Allowed files: planner flow, scenario integration, plan state, UI actions.  
> Forbidden: broad refactors outside planning state.  
> Requirements: meaningful difference between pre-wave and post-wave plans, reserve impact visible.  
> Deliver: stable demo re-plan moment.

---

## T13 — Approval receipt, audit log, and replay bookmarks (P0)
### Goal
Add seriousness and closure.

### Acceptance
- operator can approve a selected COA,
- approval generates a receipt,
- audit log records major AI and operator actions,
- replay bookmarks show major decision points,
- approval and simulation outputs preserve snapshot lineage.

### Allowed files
- audit service
- decision routes
- approval UI
- replay marker UI

### AI task card
> Objective: implement plan approval, audit logging, and replay bookmarks.  
> Allowed files: audit logic, decision routes, approval UI, replay markers.  
> Forbidden: unrelated design refactors.  
> Requirements: timestamped records, snapshot linkage, clean receipt display.  
> Done when: the demo ends with an auditable decision.

---

## T14 — Demo mode, polish, and packaging (P0)
### Goal
Maximize jury confidence and reduce live risk.

### Acceptance
- app can open directly into demo mode,
- scenario cue points are easy to trigger,
- online AI failure falls back gracefully,
- typography, spacing, and glow treatment are coherent,
- there are no dead ends in the golden path,
- the full story fits comfortably inside 7 minutes.

### Allowed files
- demo mode UI
- startup scripts
- fallback handling
- polish work across touched UI files

### AI task card
> Objective: harden the jury demo path and polish the interface.  
> Allowed files: demo mode, startup flow, fallbacks, UI polish.  
> Forbidden: major architecture rewrites.  
> Requirements: optimize for a calm 5–7 minute presentation, fast loading, no network dependency at demo time.  
> Deliver: final demo-ready build path.

---

## T15 — Future integration adapter stubs (P1 / post-demo)
### Goal
Show believable extension points without widening the hackathon MVP.

### Acceptance
- placeholder contracts exist for `sensor_update_adapter`, `track_fusion_adapter`, `effector_preview_adapter`, and `comms_resilience_adapter`,
- they are clearly marked as non-MVP and mock-only,
- they do not introduce runtime complexity into the main demo.

### Allowed files
- `packages/adapters/**`
- `docs/future_integration.md`
- contracts only

### AI task card
> Objective: add future-facing adapter stubs without changing the MVP runtime path.  
> Allowed files: adapters package, future integration docs, interface contracts.  
> Forbidden: live system integrations, network dependencies, production claims.  
> Requirements: clearly non-MVP, mockable, useful for longer-term product framing.  
> Deliver: small contract layer and short explanatory doc.

---

## 4. Recommended build order

1. T00 — Repo skeleton  
2. T01 — Contracts and event taxonomy  
3. T02 — Data normalization  
4. T03 — Scenario engine  
5. T04 — Tactical map shell + theme tokens  
6. T05 — Timeline + alerts  
7. T06 — Threat scoring  
8. T07 — Readiness + policy + suitability + guardrails  
9. T08 — COA scorecard UI with mock data  
10. T09 — Unified Copilot  
11. T10 — Explanation flow  
12. T11 — Simulation  
13. T12 — Re-plan  
14. T13 — Approval + audit  
15. T14 — Demo mode and polish  
16. T15 — Future adapter stubs if time remains

---

## 5. Suggested cadence

### Before hackday
- finish repo bootstrap,
- validate the data pack,
- wire mock mode,
- make the static tactical map render,
- test one end-to-end mock path.

### Morning of build day
Prioritize:
- scenario playback,
- alert queue,
- COA cards,
- Unified Copilot panel,
- simulation stub or mock.

### Midday
Prioritize:
- explanation,
- comparison,
- re-plan,
- approval receipt.

### Late afternoon
Prioritize:
- polish,
- demo mode,
- rehearsal,
- fallback confidence.

---

## 6. Definition of demo-ready

The build is demo-ready when:
- Boreal Passage loads,
- `scenario_alpha` plays cleanly,
- alert queue prioritizes threats,
- Unified Copilot generates 3 COAs,
- one scorecard comparison is visible,
- one why-explanation is grounded,
- one deterministic simulation runs,
- second-wave re-plan works,
- approval produces an audit receipt,
- snapshot lineage is visible,
- the neon tactical UI looks intentional,
- the story lands in under 7 minutes.
