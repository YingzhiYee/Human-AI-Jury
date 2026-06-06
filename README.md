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
OPENAI_BASE_URL=https://www.packyapi.com/v1
OPENAI_MODEL=gpt-5.4-high
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
