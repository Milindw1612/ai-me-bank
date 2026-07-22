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

- `index.html` — the entire site (single page, tabbed use-case sections, hand-authored CSS in a page-scoped `<style>` block — no framework, no Tailwind)

## Deploying

Intended to be pushed to its own GitHub repo with GitHub Pages enabled, publishing at `https://milindw1612.github.io/ai-me-bank/`. Not yet connected to a remote.
