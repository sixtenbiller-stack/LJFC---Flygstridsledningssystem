# NEON COMMAND v0.4 — Demo Script
## Target length: 5.5–6.5 minutes
## Canonical scenario: `scenario_alpha` / Two-Wave Pressure Test

---

## 1. Opening thesis (25–30s)

“NEON COMMAND is a surveillance-led air-defence planning and decision-support system.  
It helps an operator move from uncertain air picture to ranked, simulation-backed response options while preserving future readiness.  
The operator stays in control. Unified Copilot helps them decide faster and better.”

---

## 2. Show the theatre (35–40s)

Open Boreal Passage and point out:
- Arktholm as the highest-priority defended zone,
- Valbrek and Nordvik as secondary defended areas,
- Northern Vanguard, Highridge, Southern Redoubt, and Spear Point,
- Firewatch and Eastern Ridge SAM sites,
- that all data is synthetic and safe for a hackathon prototype.

Narration:
“This is a fictional operational area built for planning and simulation.  
We are not automating combat — we are improving the operator’s decision loop.”

---

## 3. Start the scenario (35–45s)

Start `scenario_alpha`.

Show:
- first tracks appearing,
- threat queue populating on the left,
- track confidence and predicted path,
- one track clearly threatening Arktholm.

Narration:
“The challenge is not just detection. It is deciding which assets to use, from which bases, with what reserve posture, before the next wave arrives.”

---

## 4. Ask Unified Copilot for plans (50–60s)

Use this prompt:

> Generate 3 ranked COAs for the current state.  
> Protect Arktholm first.  
> Keep the Spear Point QRA pair in reserve if possible.  
> Avoid committing more than 75% of currently available force unless necessary.

Show:
- exactly 3 plans,
- assigned asset mix,
- protected objectives,
- readiness cost,
- reserve posture,
- assumptions.

Narration:
“Instead of a generic chat answer, Unified Copilot returns structured plans the application can compare directly.”

---

## 5. Compare the top two COAs (45–55s)

Open the scorecard comparison view.

Highlight:
- assets committed,
- readiness remaining,
- protected value,
- reserve posture,
- risk and assumptions,
- any guardrail warning if a plan overcommits.

Narration:
“This is the core operator task: not just ‘what is the biggest threat,’ but ‘which plan protects the most value without spending the force too early?’”

---

## 6. Ask the why-question (40–50s)

Use this prompt:

> Why is Option A ranked first?  
> Cite the threat drivers, reserve trade-off, and asset bottlenecks.

Show:
- explanation drawer,
- references to track IDs,
- references to reserve posture,
- references to confidence or uncertainty.

Narration:
“The recommendation is explainable. It cites the actual threats, the selected assets, and the reserve logic behind the ranking.”

---

## 7. Simulate the top COA (45–55s)

Use this prompt or action:

> Simulate Option A with seed 42.

Show:
- outcome score,
- threats intercepted,
- zone breaches,
- readiness remaining,
- timeline of key events,
- source snapshot ID.

Narration:
“The system does not only recommend — it validates the plan in a deterministic what-if simulation starting from a frozen snapshot.”

---

## 8. Let the second wave arrive (35–45s)

Resume the scenario until the second wave appears.

Show:
- updated threat queue,
- new pressure across multiple axes,
- reduced readiness because previously committed assets are still recovering.

Narration:
“This is where the system proves it can think ahead. The first decision changes the next decision.”

---

## 9. Re-plan under pressure (45–55s)

Use this prompt:

> Re-plan with currently engaged assets unavailable.  
> Protect Arktholm, Valbrek, and Nordvik.  
> Keep the Spear Point pair in reserve if possible.

Show:
- new ranked COAs,
- visible difference from the first set,
- importance of SAM priority plus fighter reserve.

Narration:
“Now the system is balancing fighter response, SAM efficiency, and residual reserve — exactly the resource-allocation challenge in the brief.”

---

## 10. Approve one plan (20–30s)

Approve the top re-planned option.

Show:
- decision receipt,
- resulting readiness summary,
- audit entry,
- source snapshot ID.

Narration:
“The operator remains in control. The system records the chosen plan, the state that produced it, and the readiness impact.”

---

## 11. Close (20–30s)

“This improves a mission-critical workflow: understanding the air picture, comparing options, validating them through simulation, and re-planning as the situation evolves.  
That is why NEON COMMAND would help operators succeed much better, not just marginally better.”

---

## Backup path if time is tight

If the demo is running long:
- skip the long comparison narration,
- show one explanation,
- show one simulation summary,
- jump directly to wave 2 and re-plan.

---

## Backup path if online AI fails

Switch to `mock` mode and keep the same script.  
The demo should still show:
- 3 COAs,
- 1 why-answer,
- 1 simulation result,
- 1 re-plan,
- 1 approval receipt.

---

## Jury emphasis points

Make these explicit at least once:
1. Mission-critical workflow — deciding which assets to use and what to preserve.
2. Meaningful improvement — faster, more explainable, and more future-aware planning.
3. Differentiated structure — one Unified Copilot backed by structured reasoning and simulation.
4. Human-in-the-loop — recommendation, not autonomous action.
5. Narrow but believable scope — one polished slice, not a shallow platform mockup.
