# Human-AI Jury Frontend / Backend Contract

## 1. Scope

This document fixes the actual integration contract for the current Human-AI Jury repo.
It separates:

- current runnable interfaces
- compatibility/demo aliases
- missing external dependencies for live mode
- the exact validation steps we can execute

The target path is:

`Case Page -> Investigation -> Deliberation Engine -> Resolution -> Wallet / Sepolia`


## 2. Runtime Nodes

### Frontend

- App: React + Vite
- State owner: `frontend/lib/session.tsx`
- API caller: `frontend/lib/api.ts`
- User pages:
  - `frontend/case-page/CasePage.tsx`
  - `frontend/debate-page/DebatePage.tsx`
  - `frontend/resolution-page/ResolutionPage.tsx`

### Backend

- App entry: `backend/main.py`
- Primary jury endpoint: `POST /api/jury/run`
- Investigation-only endpoint: `POST /api/investigation/run`
- Readiness endpoint: `GET /api/system/readiness`

### External Providers

- OpenAI: evidence summarization, direction classification, relevance scoring
- Brave Search: news and official web retrieval
- xAPI: X/Twitter retrieval via MCP capability actions

### Chain Layer

- Current mode: frontend wallet writes directly to contract
- Contract consumer: `frontend/wallet/WalletPanel.tsx`
- Contract ABI source: `frontend/lib/contracts.ts`
- Current backend does not expose a chain write endpoint


## 3. Endpoint Matrix

| Method | Path | Caller | Purpose | Current Status |
| --- | --- | --- | --- | --- |
| `GET` | `/` | manual/debug | root info | implemented |
| `GET` | `/api/system/health` | frontend/devops | backend alive check | implemented |
| `GET` | `/api/system/readiness` | frontend/devops | dependency + key readiness | implemented |
| `GET` | `/api/jury/default-case` | Case Page | preload form values | implemented |
| `POST` | `/api/jury/run` | Case Page / Debate Page | full run: investigation + deliberation + resolution | implemented |
| `POST` | `/api/investigation/run` | backend QA / future evidence page | run investigation only | implemented |
| `GET` | `/api/demo/default-case` | compatibility only | old alias | implemented |
| `POST` | `/api/demo/run` | compatibility only | old alias | implemented |


## 4. Primary Data Contracts

### 4.1 `POST /api/jury/run`

Request body:

```json
{
  "market_id": "pm_demo_001",
  "claim": "Will Brazil win the 2026 FIFA World Cup?",
  "context": "Prediction market dispute demo",
  "prior_yes": 0.5,
  "max_items_per_agent": 4,
  "human_votes": [],
  "challenges": []
}
```

Response body:

```json
{
  "mode": "live",
  "notices": [],
  "case": {},
  "evidence_pool": {},
  "deliberation": {},
  "storage_payload": {}
}
```

Response semantics:

- `mode=live`: backend successfully used external providers
- `mode=simulated`: backend could not use live investigation and explicitly downgraded
- `notices[]`: reason for downgrade or operational hints

### 4.2 `POST /api/investigation/run`

Request body:

```json
{
  "market_id": "pm_demo_001",
  "claim": "Will Brazil win the 2026 FIFA World Cup?",
  "context": "Prediction market dispute demo",
  "max_items_per_agent": 4
}
```

Response body:

```json
{
  "success": true,
  "market_id": "pm_demo_001",
  "evidence_pool": {
    "market_id": "pm_demo_001",
    "claim": "Will Brazil win the 2026 FIFA World Cup?",
    "items": [],
    "yes_weight": 0.0,
    "no_weight": 0.0,
    "total_items": 0
  }
}
```

### 4.3 `GET /api/system/readiness`

Response body:

```json
{
  "status": "degraded",
  "service": "human-ai-jury-api",
  "env_file": "/absolute/path/.env",
  "python_version": "3.13.3",
  "platform": "macOS-...",
  "credentials": {
    "openai_api_key": false,
    "brave_api_key": false,
    "xapi_token": false
  },
  "dependencies": {
    "langgraph": false,
    "openai": false,
    "httpx": false,
    "python_dotenv": false
  },
  "live_investigation_ready": false,
  "missing": {
    "credentials": ["openai_api_key", "brave_api_key", "xapi_token"],
    "dependencies": ["langgraph", "openai", "httpx", "python_dotenv"]
  },
  "routes": {
    "jury_default_case": "/api/jury/default-case",
    "jury_run": "/api/jury/run",
    "investigation_run": "/api/investigation/run"
  }
}
```


## 5. Frontend -> Backend Mapping

### Case Page

- file: `frontend/case-page/CasePage.tsx`
- on load: `GET /api/jury/default-case`
- on submit: `POST /api/jury/run`
- output: stores `result` in session and navigates to `/debate`

### Debate Page

- file: `frontend/debate-page/DebatePage.tsx`
- action: append one human vote and/or one challenge
- rerun: `POST /api/jury/run`
- output: stores new `result` and navigates to `/resolution`

### Resolution Page

- file: `frontend/resolution-page/ResolutionPage.tsx`
- reads session result only
- no backend call yet
- chain write happens in browser wallet, not through backend


## 6. Required Environment

### Backend `.env`

Required for true live investigation:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://www.packyapi.com/v1
OPENAI_MODEL=gpt-5.4-high
BRAVE_API_KEY=...
XAPI_TOKEN=...
```

OpenAI-compatible provider note:

- backend now supports OpenAI-compatible gateways, not only the official OpenAI API
- if `OPENAI_BASE_URL` / `OPENAI_MODEL` are omitted, backend will fall back to `~/.codex/config.toml` when available
- in the current local Codex config, the provider is `https://www.packyapi.com/v1`
- for this provider, the verified chat-completions model is `gpt-5.4-high`

Current official xAPI integration note:

- The legacy REST path `https://api.xapi.to/v2/tweets/search/recent` is no longer valid for our use case.
- The current official path is the xAPI MCP endpoint:
  - `https://mcp.xapi.to/mcp?apikey=...`
- The relevant Twitter capability actions exposed there are:
  - `twitter.search`
  - `twitter.user_by_screen_name`
  - `twitter.user_tweets`

### Frontend `.env.local`

Required for local UI:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_RESOLUTION_STORAGE_ADDRESS=0x...
```


## 7. Connection Implementation Plan

### Step 1. Freeze the public contract

Content:

- use `/api/jury/*` as the frontend-facing primary contract
- keep `/api/demo/*` only as compatibility alias
- add `/api/system/readiness` so we can see whether live mode is actually possible
- remove silent frontend mock run fallback

Executable validation:

- inspect `frontend/lib/api.ts`
- inspect `backend/main.py`
- inspect `backend/api/jury_routes.py`
- inspect `backend/api/system_routes.py`

### Step 2. Make environment loading deterministic

Content:

- load `.env` before investigation agents are imported
- let `.env` override stale shell-level secrets during local dev
- strip accidental wrapping quotes from pasted API keys
- expose the loaded env file path and missing keys through readiness

Executable validation:

- inspect `backend/__init__.py`
- inspect `backend/settings.py`
- later run `curl http://127.0.0.1:8000/api/system/readiness`

### Step 3. Verify backend can start

Content:

- create a Python environment
- install backend dependencies
- run FastAPI locally

Executable validation:

- `python -m uvicorn backend.main:app --reload`
- `curl http://127.0.0.1:8000/api/system/health`

Pass condition:

- returns `status=ok`

### Step 4. Verify the full jury run endpoint

Content:

- call `/api/jury/run` with two different claims
- confirm the returned evidence pool and verdict fields change with the claim
- confirm `mode` honestly reports `live` or `simulated`

Executable validation:

```bash
curl -s http://127.0.0.1:8000/api/jury/run \
  -H 'Content-Type: application/json' \
  -d '{"market_id":"pm_a","claim":"Will Brazil win the 2026 FIFA World Cup?","context":"sports market","prior_yes":0.35,"max_items_per_agent":3,"human_votes":[],"challenges":[]}'
```

Repeat with another claim such as:

`"Will Nvidia close above $200 by December 31, 2026?"`

Pass condition:

- response payload differs in `evidence_pool.items`, `resolution.summary`, and probabilities

### Step 5. Verify frontend talks only to backend

Content:

- run Vite with `VITE_API_BASE_URL=http://127.0.0.1:8000`
- trigger a case from the browser
- confirm there is no frontend-generated fake verdict when backend is down

Executable validation:

- stop backend, submit once, confirm UI shows request failure instead of fabricated result
- restart backend, submit again, confirm request succeeds

Pass condition:

- frontend never fabricates a run result locally

### Step 6. Verify live external providers

Content:

- provide real `OPENAI_API_KEY`, `BRAVE_API_KEY`, `XAPI_TOKEN`
- restart backend
- confirm `/api/system/readiness` shows credential presence and provider auth checks separately
- rerun `/api/jury/run` and confirm `mode=live`

Executable validation:

- `curl http://127.0.0.1:8000/api/system/readiness`
- `curl http://127.0.0.1:8000/api/jury/run ...`

Pass condition:

- `provider_checks.openai.ok=true`
- `provider_checks.brave.ok=true`
- `provider_checks.xapi.ok=true`
- `live_investigation_ready=true`
- `/api/jury/run` returns `mode=live`

### Step 7. Verify chain storage

Content:

- deploy or reuse `ResolutionStorage` on Sepolia
- set `VITE_RESOLUTION_STORAGE_ADDRESS`
- connect wallet in Resolution Page
- submit the storage transaction

Executable validation:

- UI shows tx hash
- tx can be checked on a Sepolia explorer


## 8. Self-Verification Log For This Iteration

Completed and verified in this iteration:

- Step 1 contract cleanup: completed
- Step 2 env loading wiring: completed
- Step 3 backend startup: completed with Python 3.12 local venv
- Step 4 full jury run endpoint: completed in live mode with claim-dependent social evidence
- Step 5 frontend honesty check: completed
- Step 6 provider verification: partially completed

Executable checks already run locally:

- backend syntax check: `python3 -m compileall backend`
- frontend build check: `cd frontend && npm run build`
- backend dependency install:
  - `brew install python@3.12`
  - `/opt/homebrew/bin/python3.12 -m venv .venv312`
  - `./.venv312/bin/pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt`
- backend health:
  - `curl http://127.0.0.1:8000/api/system/health`
  - result: `{"status":"ok","python_version":"3.12.10","live_investigation_ready":false}`
- backend readiness:
  - `curl http://127.0.0.1:8000/api/system/readiness`
  - result summary:
    - `openai_api_key=true`
    - `brave_api_key=true`
    - `xapi_token=true`
    - `provider_checks.openai.ok=false`
    - `provider_checks.brave.ok=true`
    - `provider_checks.xapi.ok=true`
    - `live_investigation_ready=false`
- jury run claim A:
  - claim: `Will Brazil win the 2026 FIFA World Cup?`
  - result summary: `mode=live`, `social_items=3`, `verdict=NO`, `probability_yes=0.076`
- jury run claim B:
  - claim: `Did Elon Musk post about Mars this week?`
  - result summary: `mode=live`, `social_items=3`, `verdict=NO`, `probability_yes=0.06`
- frontend honesty check in browser:
  - backend stopped, clicked `Start Investigation`
  - observed UI error: `Failed to fetch`
  - observed UI behavior: snapshot stayed empty, no fabricated result appeared
  - backend restarted, clicked `Start Investigation`
  - observed navigation to `/debate`
  - observed mode banner: `simulated`
- xAPI official-path verification:
  - official tutorials reviewed in browser:
    - `https://x.com/0xAA_Science/status/2051315002137825432`
    - `https://x.com/0xAA_Science/status/2056650011753210056`
    - `https://x.com/0xAA_Science/status/2060755354867429826`
  - confirmed official usage pattern:
    - Agent / Skill / CLI / MCP flow
    - Twitter actions include `twitter.user_by_screen_name` and `twitter.user_tweets`
  - confirmed old REST endpoint returns `404 Cannot GET /v2/tweets/search/recent`
  - backend xAPI client was updated to call MCP `tools/call`
- xAPI live provider probe:
  - verified key balance with CLI:
    - `{"balance":1,"accountType":"ENTITY","tier":"BASIC"}`
  - verified key is accepted by MCP `initialize`
  - verified action discovery works through `SEARCH` / `GET`
  - verified real Twitter action calls succeed through MCP `tools/call`
  - verified `twitter.search`, `twitter.user_by_screen_name`, and `twitter.user_tweets`
- environment drift fix:
  - confirmed shell still had an older xAPI key loaded
  - updated runtime loader so `.env` overrides stale local shell values
  - updated xAPI client so token is read at instantiation time, not frozen at import time
- social retrieval quality fix:
  - replaced one-shot literal claim query with multi-query fallback strategy
  - added claim-relative freshness filtering for `today` / `yesterday` / `this week`
  - added heuristic relevance fallback so social evidence still works when OpenAI classification is unavailable
- OpenAI provider probe:
  - inspected local Codex config and confirmed model provider is OpenAI-compatible custom gateway
  - verified backend now reads `~/.codex/config.toml` fallback when `OPENAI_BASE_URL` / `OPENAI_MODEL` are absent
  - verified the gateway base URL is `https://www.packyapi.com/v1`
  - verified the listed default model `gpt-5.4` is not chat-completions compatible for this backend path
  - verified `gpt-5.4-high` succeeds with backend chat completions
  - readiness endpoint now reports:
    - `status=ready`
    - `provider_checks.openai.ok=true`
    - `llm_runtime.base_url=https://www.packyapi.com/v1`
    - `llm_runtime.model=gpt-5.4-high`

Still blocked until remaining product work is provided:

- verifying Sepolia write path with deployed contract and wallet
