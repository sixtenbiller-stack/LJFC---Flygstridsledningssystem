# LJFC COMMAND v0.4 — Consolidated Requirement Specification
##  Hackathon — Saab × 2Hero × KTH
### AI-Assisted Air Battle Planning and Air Defence Decision Support
Version: 0.4  
Date: 2026-04-14  
Audience: hackathon team, Cursor/Codex/Claude Code/Gemini/other AI development tools, demo authors, reviewers

---

## 1. Executive summary

LJFC COMMAND is a surveillance-led, map-centric, AI-assisted planning and decision-support prototype for air battle planning and air defence.

The system helps an operator:
- understand the current air picture,
- see confidence and provenance behind tracks,
- prioritize threats,
- inspect friendly readiness and constraints,
- generate ranked courses of action,
- compare those options through a scorecard,
- validate them through deterministic what-if simulation,
- re-plan when the situation changes,
- approve one plan with an audit trail.

This product is explicitly a planning, rehearsal, and decision-support system.  
It does not perform live fire-control, autonomous engagement, or combat execution.

---

## 2. Outcome of the research review

The new research input is useful, but it does **not** change the core product direction.

It mostly confirms that the current LJFC COMMAND direction is the right one:
- ontology-first state,
- one visible Unified Copilot,
- deterministic simulation adjacent to planning,
- human-in-the-loop approval,
- a narrow jury-ready golden path,
- neon-green-on-black tactical ergonomics.

The useful additions for v0.4 are narrower and practical:
1. make the event/snapshot lineage more explicit,
2. make planner guardrails more explicit,
3. make the UI token contract more explicit,
4. add future-facing adapter placeholders for surveillance and effector integration without widening hackathon scope.

### What did **not** change
- The main demo remains `scenario_alpha` / Two-Wave Pressure Test.
- The visible UI still has one Unified Copilot.
- The tactical map still defaults to SVG/Canvas over a fictional local-km grid.
- The default hackathon posture remains mock-first and deterministic.
- The build remains jury-first and ruthlessly scoped.

---

## 3. Product thesis and scope guardrails

The strongest thesis for Saab and the jury remains:

> A battle manager should be able to move from uncertain air picture to ranked, simulation-backed, explainable response options in a few interactions — while preserving future readiness and staying fully human-in-the-loop.

### Scope guardrails
The prototype shall be framed as:
- planning support,
- decision support,
- what-if simulation,
- scenario rehearsal,
- readiness management.

The prototype shall not be framed as:
- combat automation,
- autonomous engagement,
- fire-control software,
- live tactical execution,
- lethal decision delegation.

---

## 4. Canonical jury flow

The gold-path demo remains:

1. Load Boreal Passage.
2. Start `scenario_alpha`.
3. Render wave 1 tracks and prioritized alerts.
4. Ask Unified Copilot for exactly 3 COAs.
5. Compare the top 2 in a scorecard.
6. Ask why the top COA is ranked first.
7. Run a deterministic simulation from a frozen snapshot.
8. Let the second wave arrive.
9. Re-plan under degraded readiness and preserved reserve posture.
10. Approve one updated plan.
11. Show readiness impact, audit receipt, and source snapshot ID.

This is the default demo path and the default build target.

---

## 5. Required contract files

The canonical Boreal Passage runtime pack shall include at minimum:

- `geography.json`
- `assets.json`
- `scenario_alpha.json`
- `scoring_params.json`
- `policy_profiles.json`
- `effector_suitability.json`
- `planning_guardrails.json`
- `event_taxonomy.json`
- `mock_responses/situation_summary_wave1.json`
- `mock_responses/situation_summary_wave2.json`
- `mock_responses/coa_set_wave1.json`
- `mock_responses/coa_set_wave2.json`
- `mock_responses/explanation_coa_ranking.json`
- `mock_responses/simulation_result_optionA.json`
- `mock_responses/simulation_result_wave2_optionA.json`
- `schemas/coa.schema.json`
- `schemas/explanation.schema.json`
- `schemas/simulation_result.schema.json`
- `schemas/state_snapshot.schema.json`
- `schemas/audit_record.schema.json`

### New v0.4 contract clarifications
`planning_guardrails.json` should define at minimum:
- `default_max_commit_pct`
- `reserve_policy_default`
- `preserve_qra_default`
- `allow_existential_override`
- `explanation_style`

`event_taxonomy.json` should define at minimum:
- `SENSOR_UPDATE`
- `TRACK_CREATED`
- `TRACK_UPDATED`
- `ALERT_CREATED`
- `COA_REQUESTED`
- `COA_GENERATED`
- `COA_APPROVED`
- `SIM_RUN_STARTED`
- `SIM_RUN_COMPLETED`
- `ASSET_STATUS_CHANGED`
- `CONSTRAINT_CHANGED`
- `AFTER_ACTION_REVIEW_CREATED`

---

## 6. Functional requirements

## 6.1 Ontology, state, and snapshot lineage

**FR-001 (P0)** The system shall load scenario and reference data from local files without requiring network access.

**FR-002 (P0)** The system shall represent the world through typed entities, at minimum:
- Track
- Sensor
- AirBase
- City
- DefendedZone
- FriendlyAsset
- ThreatAssessment
- CourseOfAction
- SimulationRun
- Alert
- PolicyProfile
- ConstraintSet
- TerrainFeature
- AuditRecord
- StateSnapshot

**FR-003 (P0)** Every entity shall include:
- stable ID,
- type,
- side,
- current status,
- timestamps,
- provenance or source detail where relevant.

**FR-004 (P0)** The domain model shall support both current-state reads and frozen snapshot reads.

**FR-005 (P0)** Scenario state shall be replayable, pausable, and resumable.

**FR-006 (P0)** Scenario packs shall be swappable without code changes.

**FR-007 (P0)** The system shall emit typed events using the event taxonomy contract.

**FR-008 (P0)** Every COA, simulation result, explanation, approval receipt, and audit record shall reference the source snapshot that produced it using `source_state_id` or equivalent.

**FR-009 (P1)** The system should support seeded variants beyond `scenario_alpha`.

## 6.2 Surveillance and threat understanding

**FR-010 (P0)** The system shall compute a deterministic threat score for each hostile or suspected hostile track.

**FR-011 (P0)** Threat scoring shall consider, at minimum:
- heading toward defended object or zone,
- inverse time to zone,
- speed class,
- classification confidence,
- proximity to protected value,
- possible raid association.

**FR-012 (P0)** The default scoring weights in `scoring_params.json` should start at:
- heading toward defended zone: `0.30`
- inverse time to zone: `0.25`
- speed class factor: `0.15`
- confidence level: `0.15`
- target value proximity: `0.10`
- raid association bonus: `0.05`

**FR-013 (P0)** Track detail shall show:
- classification label,
- confidence,
- predicted path,
- ETA to defended zone,
- detecting sensors,
- notable anomalies or uncertainties.

**FR-014 (P0)** The system shall classify synthetic threat types including:
- unknown,
- fighter-type,
- cruise-type,
- UAV-type,
- UAV-swarm,
- decoy-suspected,
- support platform.

**FR-015 (P0)** Threat prioritization shall be explainable through structured factors, not only a final score.

**FR-016 (P1)** The system should flag special uncertainty conditions such as:
- low-confidence classification,
- suspected coordinated wave,
- probable decoy behaviour,
- probable radar-shadow or coverage-gap exploitation.

## 6.3 Common operational picture

**FR-017 (P0)** The COP shall be map-centric and use the Boreal Passage local-km grid.

**FR-018 (P0)** The COP shall display:
- terrain outlines,
- defended zones,
- cities,
- air bases,
- SAM sites,
- sensor sites,
- friendly assets,
- hostile or unknown tracks,
- predicted paths,
- selected COA overlays.

**FR-019 (P0)** The operator shall be able to:
- select an object,
- inspect details,
- focus the map from an alert,
- filter by side, type, confidence, priority, readiness, and status.

**FR-020 (P0)** The tactical map shall support play, pause, scrub, and speed controls.

**FR-021 (P0)** The event log and timeline shall stay synchronized with map playback.

**FR-022 (P0)** The operator shall be able to compare a live state with a saved or planned state.

## 6.4 Friendly assets, readiness, and policies

**FR-023 (P0)** The system shall support a balanced friendly force model across:
- fighter/interceptor assets,
- ground-based air-defence assets,
- UAV/support assets.

**FR-024 (P0)** Each asset shall expose, at minimum:
- home base,
- location,
- status,
- readiness,
- endurance or operating window,
- response tags,
- current assignment,
- recovery estimate,
- availability reason,
- basic synthetic shot or inventory state where relevant.

**FR-025 (P0)** Asset status values shall support at minimum:
- `ready`
- `standby`
- `alert`
- `active`
- `recovering`
- `unavailable`

**FR-026 (P0)** The system shall support abstract operational constraints such as:
- unavailable base,
- degraded runway,
- maintenance hold,
- communication degradation,
- reserve policy,
- weather penalty,
- depleted SAM inventory,
- delayed scramble.

**FR-027 (P0)** The system shall forecast post-plan readiness impact.

**FR-028 (P0)** The system shall explicitly show which assets remain in reserve after a COA.

**FR-029 (P0)** The system shall model and display QRA posture as a first-class planning constraint.

**FR-030 (P0)** The system shall define reusable policy profiles, at minimum:
- `protect_capital_first`
- `balanced_coverage`
- `preserve_qra_reserve`
- `minimize_readiness_depletion`

## 6.5 COA generation, guardrails, and scorecards

**FR-031 (P0)** The system shall generate exactly 3 ranked COAs for a meaningful threat state in demo mode.

**FR-032 (P0)** Every COA shall include:
- `coa_id`
- rank
- title
- summary
- actions with asset IDs and target track IDs
- protected objectives
- readiness cost
- reserve posture
- estimated outcome
- risk band
- assumptions
- rationale

**FR-033 (P0)** The operator shall be able to:
- regenerate COAs,
- exclude assets,
- lock assets,
- mark bases unavailable,
- change policy profile,
- request re-planning.

**FR-034 (P0)** The system shall detect or prevent invalid COAs such as:
- double-booked assets,
- impossible response timing,
- policy violations,
- use of unavailable assets.

**FR-035 (P0)** The default planner guardrail shall avoid committing more than `75%` of currently available force unless:
- the policy explicitly overrides it,
- or the system classifies the threat as existential,
- or the operator explicitly accepts the override.

**FR-036 (P0)** The planner shall reason at least one step ahead about reserve posture and likely next-wave pressure.

**FR-037 (P0)** The UI shall provide a COA scorecard for side-by-side comparison, showing at minimum:
- assets committed,
- protected value coverage,
- readiness remaining,
- reserve posture,
- predicted breaches,
- major assumptions,
- risk/confidence.

**FR-038 (P0)** No COA shall be auto-executed. Explicit operator approval is mandatory.

## 6.6 Unified Copilot and explanation behaviour

**FR-039 (P0)** The operator-facing assistant shall be a single visible Unified Copilot.

**FR-040 (P0)** Unified Copilot shall support the following operator intents:
- summarize the air picture,
- generate COAs,
- compare COAs,
- explain ranking,
- simulate a selected COA,
- re-plan after a change,
- answer policy and readiness questions.

**FR-041 (P0)** Unified Copilot shall return:
- structured outputs for the application,
- concise natural-language explanations for the operator.

**FR-042 (P0)** Structured outputs shall validate against repository schemas.

**FR-043 (P0)** Unified Copilot explanations shall cite:
- track IDs,
- asset IDs,
- zone IDs,
- selected policy profile or reserve rule,
- key assumptions and uncertainty notes.

**FR-044 (P0)** Explanation style shall be direct and factual. It shall avoid vague hedging and favour concrete operational trade-offs.

**FR-045 (P0)** The visible UI shall not expose a cluttered multi-agent experience.

**FR-046 (P1)** Internal tool traces may be viewable in a debug or developer mode.

## 6.7 Simulation and re-planning

**FR-047 (P0)** The prototype shall include a deterministic what-if simulation engine.

**FR-048 (P0)** The simulator shall model, at minimum:
- track movement,
- asset dispatch and engagement timing,
- defended-zone breach events,
- synthetic engagement results,
- readiness depletion and recovery,
- simple probabilistic or rule-based outcome scoring.

**FR-049 (P0)** Simulation shall be runnable from a selected COA and a frozen source snapshot.

**FR-050 (P0)** The operator shall be able to compare at least two COAs from the same frozen starting state.

**FR-051 (P0)** Simulation output shall include:
- `source_state_id`
- outcome score,
- threats intercepted,
- threats missed,
- breaches,
- asset losses if any,
- resource expenditure,
- readiness remaining,
- timeline events,
- narrative summary.

**FR-052 (P0)** The system shall support re-planning after:
- second-wave detection,
- changed availability,
- changed policy,
- changed reserve posture,
- changed threat picture.

**FR-053 (P1)** The simulator should support seeded perturbations such as:
- delayed launch,
- weather penalty,
- reduced classification confidence,
- degraded base status.

## 6.8 Audit, replay, and review

**FR-054 (P0)** The system shall create an audit record for each major operator or AI event.

**FR-055 (P0)** Audit records shall link decisions to the exact state snapshot that produced them.

**FR-056 (P0)** COA approval shall produce a decision receipt containing:
- timestamp,
- chosen COA ID,
- optional note,
- selected policy profile,
- resulting readiness summary,
- source snapshot ID.

**FR-057 (P1)** The system should support after-action review summary generation.

**FR-058 (P1)** Replay mode should allow the operator to revisit bookmarked decision points.

## 6.9 Future integration placeholders (post-hackathon, not core build scope)

**FR-059 (P1)** The architecture should reserve placeholder interfaces for a `sensor_update_adapter`.

**FR-060 (P1)** The architecture should reserve placeholder interfaces for a `track_fusion_adapter`.

**FR-061 (P1)** The architecture should reserve placeholder interfaces for an `effector_preview_adapter`.

**FR-062 (P1)** The architecture should reserve placeholder interfaces for a `comms_resilience_adapter`.

**FR-063 (P1)** These adapter contracts are for product credibility and future extension only; they are not part of the hackathon MVP.

---

## 7. Hackathon build requirements

These are the must-build requirements for the strongest jury demo.

**BUILD-001 (P0)** The system shall load the canonical Boreal Passage JSON pack locally.

**BUILD-002 (P0)** The system shall render a 2D tactical display in a neon-green-on-black visual style.

**BUILD-003 (P0)** The tactical display shall use SVG or Canvas by default over the local-km grid.

**BUILD-004 (P0)** The system shall support play, pause, scrub, and speed control for `scenario_alpha`.

**BUILD-005 (P0)** The alert queue shall show prioritized threats with:
- track ID,
- class,
- priority,
- ETA,
- threat score.

**BUILD-006 (P0)** Selecting an alert shall focus the corresponding track on the map.

**BUILD-007 (P0)** Track detail shall show confidence and detecting sensor provenance.

**BUILD-008 (P0)** The right panel shall expose Unified Copilot actions for:
- `Generate COAs`
- `Why this plan?`
- `Simulate`
- `Re-plan`
- `Approve`

**BUILD-009 (P0)** The COA response shall show exactly 3 ranked options in a meaningful scenario state.

**BUILD-010 (P0)** At least one scorecard comparison view shall compare 2 COAs side by side.

**BUILD-011 (P0)** The simulator shall run deterministically from a fixed seed.

**BUILD-012 (P0)** The second wave in `scenario_alpha` shall trigger visible re-planning pressure.

**BUILD-013 (P0)** A changed constraint, such as unavailable assets or preserved QRA reserve, shall regenerate COAs.

**BUILD-014 (P0)** Approval shall create an audit receipt shown in the UI.

**BUILD-015 (P0)** The golden-path demo shall work in `mock` mode without online LLM access.

**BUILD-016 (P0)** The app shall start locally with one documented command.

**BUILD-017 (P0)** The default startup path shall open directly into a jury-ready demo mode or clearly expose it.

**BUILD-018 (P0)** The explanation view shall be reachable within at most two interactions from a selected COA.

**BUILD-019 (P0)** Demo-mode planning shall honour `planning_guardrails.json`, including reserve posture and the default overcommit guardrail.

**BUILD-020 (P0)** Simulation output and approval receipt shall visibly preserve snapshot lineage.

**BUILD-021 (P0)** The full story shall be demonstrable in under 7 minutes.

---

## 8. UI and UX requirements

## 8.1 Visual identity

**UI-001 (P0)** The dominant interface style shall be neon green on black or near-black.

**UI-002 (P0)** The product shall deliberately avoid the generic dark-blue AI dashboard aesthetic.

**UI-003 (P0)** The visual feel shall be:
- premium,
- tactical,
- crisp,
- readable,
- not retro-terminal parody.

**UI-004 (P0)** Warning states may use amber and red, but green-on-black remains the dominant palette.

**UI-005 (P0)** Grid, glow, and scanline effects must remain subtle and not reduce legibility.

### Recommended default tokens
The default theme should approximate:

- `--bg-primary`: `#020402` to `#050806`
- `--surface`: `#0A0F0A`
- `--neon-green`: `#39FF14`
- `--green-secondary`: `#1ED760` to `#7CFFB2`
- `--amber-warning`: `#FFC857`
- `--red-critical`: `#FF5A5F`
- `--neutral`: `#A0A0A0` to `#E0E0E0`

## 8.2 Layout

**UI-006 (P0)** The default layout shall be:
- left: alerts / threat queue
- center: tactical map
- right: Unified Copilot / COA / explanation / selection panel
- bottom: timeline / event log / playback controls

**UI-007 (P0)** The map shall remain the primary focal area.

**UI-008 (P0)** The operator shall be able to reach a “Why this recommendation?” view within one or two interactions.

**UI-009 (P0)** A side-by-side COA comparison view shall be supported.

**UI-010 (P1)** Replay mode should be visually distinct from live or simulated state.

---

## 9. Non-functional requirements

**NFR-001 (P0)** The project shall support `mock`, `openrouter`, `google`, and `ollama` execution modes.

**NFR-002 (P0)** `mock` mode shall be deterministic and demo-safe.

**NFR-003 (P0)** All secrets shall be loaded from environment variables only.

**NFR-004 (P0)** The system shall preserve reproducibility through fixed seeds for simulation.

**NFR-005 (P0)** Prompts, structured inputs, outputs, and failures shall be logged in developer mode.

**NFR-006 (P0)** The codebase shall be modular enough for AI-assisted tools to work on:
- frontend,
- API,
- simulation,
- domain,
- data,
- prompt/schema contracts
with minimal cross-task confusion.

**NFR-007 (P0)** The system shall run comfortably on a normal developer laptop using demo-scale synthetic data.

**NFR-008 (P0)** The preferred implementation shall avoid unnecessary dependencies on online maps or tile services.

**NFR-009 (P0)** The online provider chain should degrade cleanly from `openrouter/google` to `ollama` to `mock` without breaking the UI.

**NFR-010 (P1)** Future adapter placeholders should be mockable without introducing real integration risk.

---

## 10. Recommended architecture

## 10.1 Default reference stack
Recommended default:
- Frontend: React + TypeScript + SVG/Canvas tactical map
- API/orchestration: FastAPI or Node/TypeScript
- Simulation: Python preferred for deterministic simulation logic
- Shared contracts: JSON schema + typed domain models
- State updates: REST + WebSocket or equivalent event stream

## 10.2 Default repository layout

```text
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
```

## 10.3 LLM integration modes
Supported modes:
- `mock` — default demo-safe mode
- `openrouter` — preferred hackathon online path
- `google` — optional direct Google AI Studio path
- `ollama` — local fallback path

## 10.4 Tactical-map decision
Because Boreal Passage is a fictional local coordinate grid, the implementation should treat the map as a custom operational display, not a geospatial web map by default.

## 10.5 Future integration posture
Any future sensor or effector interface should remain a placeholder contract or mock adapter in the hackathon build. No live system integration is required or expected.

---

## 11. Acceptance criteria

### 11.1 Demo-critical acceptance

**AC-001** Boreal Passage loads with terrain, bases, zones, cities, assets, and tracks.

**AC-002** `scenario_alpha` plays through wave 1 and wave 2 using local data.

**AC-003** Threat scoring populates the alert queue automatically.

**AC-004** Unified Copilot generates 3 ranked COAs.

**AC-005** At least one COA comparison scorecard is visible.

**AC-006** A why-question returns a grounded explanation with references to tracks, assets, policy, or reserve posture.

**AC-007** A deterministic simulation runs for a selected COA.

**AC-008** Re-planning occurs after the second wave or changed constraint.

**AC-009** Approval creates an audit receipt.

**AC-010** The UI clearly reads as neon green on black.

**AC-011** The explanation path is accessible within two interactions.

**AC-012** The planner visibly respects reserve or overcommit guardrails unless an override is explicit.

**AC-013** Simulation and approval outputs preserve snapshot lineage.

**AC-014** The full demo lands in under 7 minutes.

**AC-015** The demo still works in `mock` mode without online AI.

### 11.2 Stretch acceptance

**AC-016** Additional scenarios beyond `scenario_alpha` are supported.

**AC-017** Replay bookmarks are supported.

**AC-018** Policy profiles can be switched from the UI.

**AC-019** Tool traces can be inspected in developer mode.

**AC-020** Future adapter placeholders exist in code or contracts.

---

## 12. Final positioning line

**LJFC COMMAND turns uncertain surveillance data into ranked, simulation-backed, explainable air-defence plans — through one Unified Copilot, explicit reserve-aware planning logic, and a command-grade neon tactical interface built to impress Saab and the jury.**
