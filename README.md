# Ai-ME BANK — Agentic AI Use Cases

A CXO strategy brief presenting 3 Agentic AI use cases for a banking client, consolidated from 5 independent LLM analyses:

1. **MSME Credit CAM Prep** — 5-day loan file assembly compressed to under 4 hours
2. **Fraud Detection & Investigation** — sub-60-second fraud-probability scoring
3. **Collections & Delinquency Recovery** — 100% daily portfolio coverage vs. 20–30% manual reach

## Running it

Static HTML, no build step, no dependencies. Just open `index.html` in a browser, or serve it with any static file server, e.g.:

```
python -m http.server 8000
```

then visit `http://localhost:8000`.

## Structure

```
ai-me-bank/
├── index.html          the site (GitHub Pages serves this)
├── README.md
└── agentic-ai/          Python backend — see agentic-ai/README.md
    ├── main.py
    ├── a1_msme_credit/
    ├── a2_fraud_detection/
    ├── a3_collections_recovery/
    └── shared/
```

`agentic-ai/` is source code only — a FastAPI + LangGraph implementation of the 3 use cases, browsable on GitHub but not served by Pages (which only serves static files). See [`agentic-ai/README.md`](agentic-ai/README.md) for how to run it.

## Deploying

Intended to be pushed to its own GitHub repo with GitHub Pages enabled, publishing at `https://milindw1612.github.io/ai-me-bank/`. Not yet connected to a remote.
