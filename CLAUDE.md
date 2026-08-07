# Ai-ME BANK — Project Reference

## What this is

Ai-ME BANK is an illustrative agentic AI platform for a regulated Indian bank — built as a live, working demonstration of how a Chief AI Officer would design, cost, govern, and scale an enterprise AI program, not a real bank or a real deployment. It's a static HTML/CSS/JS site (no build step, no backend in production) hosted on GitHub Pages at `https://milindw1612.github.io/ai-me-bank/`, plus a small illustrative Python backend under `agentic-ai/` showing what the agents would actually look like in code.

**The 3 flagship pilots** (the only real "built" use cases — everything else is roadmap/future scope):
1. **MSME Credit CAM Prep** — 4 agents, credit memo drafting for MSME lending
2. **Fraud Detection & Investigation** — 4 agents, real-time fraud scoring
3. **Collections & Delinquency Recovery** — 4 agents, outreach and negotiation

None of the 3 pilots have actually gone live — the site is explicit about this everywhere (see Governance → Validation Gates). Don't let new content imply otherwise.

**The AI Governance Supervisor** (`governance-supervisor.html`) is a *design proposal*, not a built system — an orchestrator + 5 specialist agents (Compliance Mapping, Program Tracking, Agent Fleet Monitor, Audit & Assurance, and an event-triggered Intake & Integration agent) that would supervise the whole Day 0 → Year 3 program. It is explicitly never called "accountable" — RBI FREE-AI Sutra 5 requires named human accountability, so this system is framed as responsible for *visibility* only; the CAIO/Board/CEO always take the call.

## Site map

| Page | Purpose |
|---|---|
| `index.html` | Use-case overview, entry point |
| `board-brief.html` | One-page CXO/Board summary — the "start here" walkthrough page |
| `blueprints.html` | Per-pilot technical blueprints + value-calculation working tables |
| `architecture.html` | Shared platform architecture |
| `aws-architecture.html` | AWS-specific security/network architecture deep-dive |
| `roi.html` | Return-on-investment detail per pilot |
| `cost.html` | Build/running cost breakdown, TCO, Resource & Team Rate Cards |
| `timeline.html` | Traditional vs AI-accelerated build Gantt, resource deployment plan |
| `governance.html` | HITL, PII, Risk Tiers, Validation Gates, Audit Trail |
| `compliance.html` | RBI/MeitY/SEBI/IRDAI/CERT-In/DPDP regulatory mapping |
| `ai-gpolicy.html` | Full 24-section board-level AI Governance Policy + Annexures A–J |
| `roadmap.html` | 0–36 month enterprise roadmap, 8 pillars, operating model RACI |
| `governance-checklist.html` | Day 0 → Year 3 tickable compliance checklist (consolidates the above) |
| `governance-supervisor.html` | AI Governance Supervisor design proposal (orchestrator + 5 agents) |
| `deploy-guide/*.html` | 7-part AWS deployment runbook + ownership RACI |
| `helicopter.html` | High-level architecture flyover |
| `ai-mindmap.html` | AI-readiness decision tree |
| `glossary.html` | Term definitions |
| `contact.html` | Contact info |

## Design system

Oxblood Wine dark theme, defined identically in every page's `:root`:
```
--bg:#3B0F1A --surface:#4A1420 --gold:#F59E0B --teal:#0D9488 --green:#34D399
--purple:#A78BFA --red:#F87171 --amber:#FBBF24 --blue:#2D6BE4 --neon:#39FF14 (logo only)
```

Every page shares the same `<nav>`/`.nav-links`/footer HTML block — copy from the newest existing page (currently `governance-supervisor.html`) rather than reconstructing it. Root pages use bare `href="page.html"`; `deploy-guide/*.html` pages use `href="../page.html"`. New nav items go last, immediately before "Contact Me."

Reusable CSS classes, already defined site-wide — reuse, don't reinvent:
- `.note-box` / `.plain-box` — callout boxes (gold-left-border warning vs teal "in plain English")
- `.pill-*` — colored status/category tags
- `.table-scroll` + `table` — the standard data-table pattern
- `.tab-btn` / `.tab-panel` + `showTab()` JS — the standard tabbed-page pattern (used on `governance.html`, `roadmap.html`, `compliance.html`, `aws-architecture.html`, `governance-checklist.html`, `governance-supervisor.html`)

Multi-page tabbed sites use a hash-router (`activateFromHash()`) so `page.html#tab-id` cross-links land on the right tab.

## Regulatory/standards mapping

Full detail lives on `compliance.html` — treat it as the single source of truth, don't duplicate framework detail elsewhere:
- **RBI FREE-AI Framework** (13 Aug 2025) — 7 Sutras, 6 Pillars, 26 recommendations. Only the 7 Sutras and 6 Pillars are documented at a sourced/citable level; the 26 individual recommendations are not individually enumerated anywhere in the source material — never fabricate specific numbered clauses.
- **MeitY India AI Governance Guidelines**, **SEBI AI/ML consultation**, **IRDAI** (emerging), **CERT-In AI-era blueprint**, **DPDP Act 2023 & Rules 2025**, **international MRM benchmarks** (US SR 11-7, UK SS1/23) — all mapped per-clause to the roadmap on `compliance.html`'s "Compliance by Lifecycle Stage" tab.

## Key figures — always point, never re-derive

Financial and timeline figures live in exactly one place each — pull from there, don't hardcode a copy on a new page:
- Build cost, running cost, TCO, payback → `cost.html`
- Per-use-case ROI/value ranges and their bottom-up derivation → `roi.html` / `blueprints.html`'s calculation tables
- Build durations, milestones, resource deployment → `timeline.html`

If a new page needs one of these numbers, link to the source page rather than repeating the figure — this is how the site has stayed internally consistent across many rounds of edits.

## Standing conventions (established over this project's build history)

- **Honesty discipline**: never state or imply something is "done," "live," or "complete" that hasn't actually happened. The 3 pilots are pre-launch; Validation Gates are unrun. Where a new supporting figure is introduced that isn't already published elsewhere, tag it explicitly as an assumption (see the `.pill-assumption` / `.pill-existing` pattern on `blueprints.html`'s calculation tables).
- **Git process**: only commit/push when the user explicitly asks. Always exclude `B2 - Claude AI Mastery Kit (1).pdf` and any stray `.docx`/lock files from staging — they aren't part of the site.
- **Link integrity**: run the link/anchor audit script (in the session scratchpad, checks every `href` against real files and anchor IDs) after any nav or cross-link change.
- **Public-facing content** (LinkedIn posts, resume text, external write-ups) about this project must use approximate/rounded figures, not exact ones, and must never describe the internal architecture, flow, or component sequence in enough detail to be replicable via an LLM.
- **GitHub Pages deploys can fail silently** — a successful `git push` does not guarantee the Pages deployment succeeded. If asked to verify a push is live, check the actual deployed page content, not just the push result.
