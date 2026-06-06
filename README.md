# Human-AI Jury
> A Human-AI Consensus Network for Disputed Events

## What is Human-AI Jury?
Human-AI Jury resolves ambiguous real-world events through evidence, debate, and transparent consensus.
AI agents gather evidence.
Humans challenge conclusions.
A Judge Agent produces an auditable verdict.

## Why?
Prediction markets, governance systems, and online communities frequently face disputed events.
Current solutions rely on:
- centralized moderators
- token voting
- black-box AI
Human-AI Jury introduces a transparent alternative.

## Architecture
Case

↓

Evidence Agents

↓

Prosecution & Defense

↓

Human Jury

↓

Judge Agent

↓

Resolution

↓

Ethereum

## Features
- Multi-Agent Investigation
- Human-in-the-Loop Deliberation
- Evidence Graph
- Transparent Reasoning
- Confidence-Based Resolution
- On-Chain Verification

## Tech Stack
Frontend:
- React
- Tailwind
- Wagmi

Backend:
- FastAPI
- LangGraph

AI:
- GPT-5.4
- xAPI

Blockchain:
- Ethereum
- Sepolia

## Demo
Example:
Did Trump pardon Hunter Biden before January 20?
Human-AI Jury collects evidence, facilitates debate, and generates an explainable verdict.

## Vision
Human-AI Jury aims to become the dispute resolution layer for prediction markets, DAOs, and online communities.

## Local Setup

### Prerequisites
- Python 3.12
- Node.js 18+
- `npm`

### Backend Environment

Create a local `.env` in the repo root:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
OPENAI_MODEL=...
BRAVE_API_KEY=...
XAPI_TOKEN=...
```

Notes:
- `OPENAI_BASE_URL` and `OPENAI_MODEL` are optional if your local Codex config already points to the same provider.
- The backend now supports OpenAI-compatible gateways such as PackyAPI.

### Install Dependencies

Backend:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv312
./.venv312/bin/pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

### Start The Project

Start the backend from the repo root:

```bash
./.venv312/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

- Frontend: `http://127.0.0.1:5173`
- Backend readiness: `http://127.0.0.1:8000/api/system/readiness`

### Quick Verification

Check backend readiness:

```bash
curl -s http://127.0.0.1:8000/api/system/readiness | jq '{status, llm_runtime, provider_checks}'
```

Run one live jury case:

```bash
curl -s http://127.0.0.1:8000/api/jury/run \
  -H 'Content-Type: application/json' \
  -d '{"market_id":"pm_brazil","claim":"Will Brazil win the 2026 FIFA World Cup?","context":"sports prediction dispute","prior_yes":0.5,"max_items_per_agent":2,"human_votes":[],"challenges":[]}' | jq '{mode, verdict: .deliberation.resolution.verdict, probability_yes: .deliberation.resolution.probability_yes}'
```

### Secret Safety

Before committing, run:

```bash
bash scripts/scan_secrets.sh
```

This scan is intentionally lightweight. It is meant to catch obvious pasted keys before they enter git history.

## Public API Deployment

This repo includes a production-minded Render blueprint in [render.yaml](/Users/yyz/code/Human-AI-Jury/render.yaml) so the backend can be deployed directly from GitHub and exposed as a public API.

### What Gets Deployed

- Public FastAPI service: `human-ai-jury-api`
- Public endpoints:
  - `/api/jury/run`
  - `/api/system/readiness`
  - `/api/system/health`
  - `/docs`

### Deploy On Render

1. Push this repository to GitHub.
2. In Render, choose `New > Blueprint`.
3. Connect the GitHub repo and select `render.yaml`.
4. Fill in the required secrets in the Render dashboard:
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL` if you use an OpenAI-compatible gateway such as PackyAPI
   - `OPENAI_MODEL` if your provider needs a specific model such as `gpt-5.4-high`
   - `BRAVE_API_KEY`
   - `XAPI_TOKEN`
5. Wait for the initial deploy to finish.

### After Deploy

If your Render URL is `https://human-ai-jury-api.onrender.com`, the public story becomes:

- Health check:
  - `https://human-ai-jury-api.onrender.com/api/system/health`
- Readiness and dependency transparency:
  - `https://human-ai-jury-api.onrender.com/api/system/readiness`
- Interactive API docs:
  - `https://human-ai-jury-api.onrender.com/docs`
- Main verdict API:
  - `https://human-ai-jury-api.onrender.com/api/jury/run`

Example request:

```bash
curl -s https://human-ai-jury-api.onrender.com/api/jury/run \
  -H 'Content-Type: application/json' \
  -d '{"market_id":"pm_demo","claim":"Will Brazil win the 2026 FIFA World Cup?","context":"sports prediction dispute","prior_yes":0.5,"max_items_per_agent":2,"human_votes":[],"challenges":[]}'
```

### Why This Helps The Demo

- GitHub shows the code and architecture.
- Render gives you a real public API URL.
- FastAPI `/docs` makes the system demoable for judges and external developers without extra frontend setup.
- `/api/system/readiness` shows provider status, which strengthens the transparency story.

## GitHub Pages Frontend

If you want the simplest public demo setup, use:

- Frontend: GitHub Pages
- Backend API: Render

This repo already includes a Pages workflow in [.github/workflows/deploy-pages.yml](/Users/yyz/code/Human-AI-Jury/.github/workflows/deploy-pages.yml).

### What It Does

- builds `frontend/`
- publishes the static app to GitHub Pages
- points frontend API requests to:
  - `https://human-ai-jury-api.onrender.com`

### One-Time Setup

1. Open GitHub repository `Settings > Pages`
2. Under `Build and deployment`, set `Source` to `GitHub Actions`
3. Push to `main`
4. Wait for the `Deploy Frontend to GitHub Pages` workflow to finish

The expected project site URL is:

- `https://yingzhiyee.github.io/Human-AI-Jury/`

### Notes

- The frontend now uses hash routing, so GitHub Pages refreshes will not break sub-pages.
- Static assets are built with base path `/Human-AI-Jury/`, which matches project-site deployment on GitHub Pages.
- If your backend URL changes, update `VITE_API_BASE_URL` in the workflow file.
