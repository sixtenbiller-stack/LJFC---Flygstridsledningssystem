# LJFC COMMAND

**AI-First Air Battle Planning and Decision Support**

*Repository: **LJFC — Flygstridsledningssystem** — [GitHub](https://github.com/sixtenbiller-stack/LJFC---Flygstridsledningssystem)*

LJFC COMMAND is a surveillance-led, map-centric, AI-first planning and decision-support prototype for air battle planning and air defence. A proactive **Unified Copilot** (Chief of Staff) continuously monitors the scenario and provides concise updates, while the operator retains full decision authority.

## Quick Start

```bash
# One command:
make dev

# Or:
./scripts/run_demo.sh
```

Then open **http://192.168.68.59:3900** (or https://peace-keeper.app)

## Requirements

- Python 3.11+
- Node.js 18+
- npm

## Environment Variables

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | For AI mode | Google Gemini API key |
| `GEMINI_MODEL` | No | Override model (default: `gemini-2.5-flash`) |

Also accepts `GOOGLE_AI_STUDIO_KEY` or `GOOGLE_API_KEY`. Without a key, the system runs in mock mode with deterministic fallback responses.

## Architecture

- **Frontend**: React + TypeScript + Vite (port 3900)
- **Backend**: FastAPI + Pydantic + Uvicorn (port 8000)
- **AI Provider**: Gemini (default) with mock fallback
- **Map**: SVG tactical display on local-km grid (Boreal Passage)
- **Data**: Local JSON files (no external services required)

### Backend Services

| Service | Purpose |
|---------|---------|
| `gemini_provider` | AI provider abstraction with Gemini SDK + fallback |
| `chief_of_staff_service` | Proactive feed with materiality scoring |
| `command_router` | Slash command + NL intent parsing |
| `copilot_service` | COA generation, explanation, simulation |
| `scenario_engine` | Deterministic event-driven playback |
| `threat_scorer` | Weighted threat scoring |
| `audit_service` | Decision audit trail with snapshot lineage |

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/state` | Current scenario state |
| GET | `/alerts` | Enriched threat alerts |
| GET | `/coas` | Current COAs |
| GET | `/decisions` | Audit log |
| POST | `/scenario/load` | Load scenario |
| POST | `/scenario/control` | Play/pause/reset/speed |
| POST | `/agent/coas` | Generate COAs |
| POST | `/agent/explain` | Explain COA ranking |
| POST | `/agent/simulate` | Run simulation |
| POST | `/decision/approve` | Approve COA |
| GET | `/copilot/feed` | Chief of Staff feed |
| POST | `/copilot/command` | Operator command/question |
| GET | `/copilot/status` | AI provider status |

## AI Modes

| Mode | When | Description |
|------|------|-------------|
| **Gemini** | `GEMINI_API_KEY` set | Full AI: proactive updates, NL answers, grounded explanations |
| **Mock** | No key or Gemini fails | Deterministic JSON responses, structured fallback summaries |

The demo works fully offline in mock mode. All COA generation, explanation, simulation, and approval flows work in both modes.

## Copilot Commands

### Slash Commands
`/summary` `/top-threats` `/generate-coas` `/why [coa-id]` `/simulate [coa-id]`
`/compare [id1] [id2]` `/replan` `/what-changed` `/recommend` `/focus [id]`
`/brief` `/approve [coa-id]` `/reserve [n]` `/policy [name]`

### Natural Language
"What changed in the last 30 seconds?" · "Which threat most endangers Arktholm?" ·
"Generate plans but keep one interceptor pair in reserve." · "Give me a commander's brief."

## Demo Scenario

The default scenario is **Boreal Passage — Two-Wave Pressure Test** (`scenario_alpha`):

1. Open LJFC COMMAND and view the tactical map
2. Start scenario playback — hostile tracks appear
3. **Chief of Staff** posts proactive threat assessments
4. Threat alerts populate automatically
5. Generate 3 ranked Courses of Action (COAs)
6. Compare top 2 COAs side-by-side
7. Ask "Why is this ranked first?"
8. Run deterministic simulation
9. Second wave arrives — Chief of Staff alerts operator
10. Re-plan under degraded readiness
11. Approve a plan with full audit trail
12. Type questions or commands at any time

## Project Structure

```
frontend/          React + Vite + TypeScript UI
backend/           FastAPI + Python services
neon-command-data/  Scenario data and mock responses
scripts/           Startup scripts
```

## Safety

This is a hackathon prototype using synthetic data only. It is not a combat system, not an autonomous engagement system, and not connected to any real-world systems. Operator approval is mandatory for all plan execution.
