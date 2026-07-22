# Ai-ME BANK — Agentic AI Backend

LangGraph + FastAPI implementation of the 3 use cases presented on the site (`../index.html`):

| # | Use Case | Agents | Entry Route |
|---|---|---|---|
| A1 | MSME Credit CAM Prep | Financial Ingestion → Bureau/Tax Verification → Risk/Cash-Flow → CAM Drafting → human sign-off | `POST /msme-credit/apply` |
| A2 | Fraud Detection & Investigation | Device/IP + Behavior + Merchant/AML (parallel) → Recommendation → auto-action or analyst escalation | `POST /fraud/score` |
| A3 | Collections & Delinquency Recovery | Risk/Behavior → Channel → Negotiation → escalation if outside policy band | `POST /collections/process` |

## Structure

```
agentic-ai/
├── main.py                     entrypoint, mounts all 3 routers
├── a1_msme_credit/              Use Case #1
├── a2_fraud_detection/          Use Case #2
├── a3_collections_recovery/     Use Case #3
└── shared/                      config, LLM client, PII middleware, DB, models
```

Each use case folder follows the same shape: `states.py` (LangGraph state), `tools.py` (external API adapters), one file per sub-agent, `coordinator.py` (graph assembly + entry function), `router.py` (FastAPI endpoints).

## Running locally

```
cp .env.example .env   # fill in real API keys
docker compose up --build
```

API docs at `http://localhost:8000/docs` once running.

## Security

PII (customer name, PAN, Aadhaar, account/card numbers) is tokenised at the API boundary (`shared/middleware.py`) and never enters an LLM prompt — `safe_json()` scrubs sensitive fields before any data is included in a Claude call. Final decision authority (credit sign-off, confirmed-fraud calls, settlement outcomes) stays human in every use case; the agents draft, score, and recommend — they don't unilaterally decide.
