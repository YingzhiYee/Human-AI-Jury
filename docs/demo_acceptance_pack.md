# Human-AI Jury Demo And Acceptance Pack

Validated on June 7, 2026.

## Public Entry Points

- Frontend: `https://yingzhiyee.github.io/Human-AI-Jury/`
- Public API: `https://human-ai-jury-api.onrender.com`
- API docs: `https://human-ai-jury-api.onrender.com/docs`
- Sepolia contract: `https://sepolia.etherscan.io/address/0x76Bcbb0b0E44fdd6626dd709C59d396d03eFF086`

## Recommended Demo Order

1. Open the public frontend and show the Case page.
2. Enter a fresh case and run the jury pipeline.
3. Show the Debate page:
   - Prosecutor Agent
   - Defense Agent
   - evidence pool
   - Human Jury input panel
4. Open the Resolution page and show:
   - verdict
   - YES probability
   - final confidence
   - audit trail
   - Sepolia storage panel
5. End by showing the public API docs and the deployed contract link.

## Primary Demo Case

### Case A: Bitcoin threshold prediction

- Claim:
  `Will Bitcoin trade above $150,000 before December 31, 2026?`
- Context:
  `Crypto price prediction dispute`
- Why this is the best main demo:
  - it is easy for judges to understand immediately
  - it naturally produces supporting and opposing evidence
  - it showcases the deliberation engine better than a binary historical fact question

Validated live result on June 7, 2026:

- verdict: `YES`
- probability_yes: `0.98`
- final_confidence: `0.697`
- yes_weight: `2.4`
- no_weight: `1.0`
- current notice:
  `No social/X evidence was included in this live run. xAPI may have returned no matches, or the social provider may be unavailable or limited.`

What to point out while demoing:

- the case is not hardcoded; the frontend sends this exact claim to the public API
- the evidence pool contains both bullish and bearish items
- the Prosecutor and Defense arguments are generated from the current evidence, not static copy
- the Resolution page computes a deterministic hash for Sepolia storage

## Backup Demo Cases

### Case B: Brazil World Cup prediction

- Claim:
  `Will Brazil win the 2026 FIFA World Cup?`
- Context:
  `Sports prediction dispute`

Validated live result on June 7, 2026:

- verdict: `YES`
- probability_yes: `0.976`
- final_confidence: `0.834`
- yes_weight: `1.275`
- no_weight: `0`

Why keep it as backup:

- it is intuitive for non-technical judges
- it tends to produce a clean story quickly
- it is good when you want a simpler narrative than the crypto case

### Case C: Human-in-the-loop rerun

Use either Case A or Case B first, then go to the Debate page and add:

- one juror vote
- one challenge summary

Recommended human input:

- juror stance: `NO`
- juror confidence: `0.90` to `0.95`
- challenge target: `YES`
- challenge severity: `0.70` to `0.80`

Suggested juror comment:

`The current evidence is forecast-heavy and does not fully justify settlement confidence.`

Suggested challenge summary:

`Several supporting items are speculative projections rather than settlement-grade evidence.`

Expected acceptance behavior:

- the rerun completes successfully
- `human_votes` and `challenges` are included in the new request
- the new resolution is not identical to the original run
- at least one of these values changes:
  - `probability_yes`
  - `final_confidence`
  - `audit_trail`

## Cases To Avoid In A Timed Demo

### GPT-6 release prediction

Claim:

`Will OpenAI release a GPT-6 model before December 31, 2026?`

Why not use it as the main demo:

- live response time was noticeably less stable during validation on June 7, 2026
- it is more dependent on current web evidence quality and provider latency

## Acceptance Checklist

### 1. Public frontend is reachable

Action:

- open `https://yingzhiyee.github.io/Human-AI-Jury/`

Pass condition:

- Case, Debate, and Resolution navigation render correctly

### 2. A fresh claim triggers a real backend request

Action:

- change the claim on the Case page
- click `Start Investigation`

Pass condition:

- the app navigates to Debate
- the Debate page text includes the new claim
- the arguments are different from the previous case

### 3. Live evidence is not hardcoded

Action:

- inspect the Debate page evidence pool
- or call `POST /api/jury/run` directly from the public API

Pass condition:

- titles, summaries, and source links match the current claim
- different claims produce different evidence pools

### 4. Resolution is generated from the run

Action:

- open the Resolution page after a live run

Pass condition:

- verdict, probability, confidence, and audit trail are visible
- the question shown on the page matches the claim just submitted

### 5. Human input changes the deliberation state

Action:

- on Debate, add a juror comment and a challenge summary
- click `Apply Human Input`

Pass condition:

- the app reaches Resolution again
- the final payload differs from the previous one
- the audit trail mentions human input or challenge pressure

### 6. Sepolia storage panel is wired

Action:

- open the Resolution page

Pass condition:

- the contract address is visible
- the resolution hash is visible
- `Store Resolution` becomes actionable after wallet connection

### 7. Public API is externally usable

Action:

- open `https://human-ai-jury-api.onrender.com/docs`

Pass condition:

- `POST /api/jury/run`
- `GET /api/system/readiness`
- `GET /api/system/health`
  are all visible in the docs UI

## API Payload For External Demo

```bash
curl -s https://human-ai-jury-api.onrender.com/api/jury/run \
  -H 'Content-Type: application/json' \
  -d '{
    "market_id": "pm_demo_public",
    "claim": "Will Bitcoin trade above $150,000 before December 31, 2026?",
    "context": "Crypto price prediction dispute",
    "prior_yes": 0.5,
    "max_items_per_agent": 4,
    "human_votes": [],
    "challenges": []
  }'
```

## xAPI Acceptance Placeholder

When you send the X tutorials, we should add one more section here:

- which xAPI capability the tutorial proves
- which project feature it maps to
- how to reproduce it inside Human-AI Jury
- what the pass condition is

Right now the system already surfaces xAPI dependency state through:

- `GET /api/system/readiness`
- live run notices on Debate and Resolution pages

## Current Demo Story In One Sentence

Human-AI Jury turns a disputed claim into a transparent verdict by combining live multi-agent evidence gathering, adversarial AI debate, human challenge input, and optional Sepolia storage.
