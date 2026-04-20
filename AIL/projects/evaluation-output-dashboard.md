---
type: project
tags: [project]
status: active
priority: medium
created: 2026-04-19
updated: 2026-04-19
owner: Landon
summary: "Turn Alfie evaluation output from raw text into a comprehensive dashboard — per Ken's 2026-04-19 ask"
---

# Evaluation Output Dashboard

## Goal

Ken's ask (2026-04-19): evaluation output should be a dashboard or something comprehensive, not raw output. Build a view that surfaces eval results in a way a non-engineer executive can scan and draw conclusions from.

## Key People

- [[people/Ken Akoundi|Ken]] — requester, primary audience
- [[people/Zeki|Zeki]] — technical stakeholder; any dashboard lives alongside the eval pipeline he oversees
- [[people/Devon|Devon]] — Head of Product; could inform what a "product-grade" eval view looks like

## Related Modules

- Evaluation pipeline (Alfie) — need to trace the current output format and where it emits
- LangGraph / LangChain — whatever's producing the eval traces currently

## Tasks

- [ ] Clarify with Ken: what decisions does he want to make from this dashboard? (Trends over time? Regressions? Drill into failure cases? Benchmark comparisons?)
- [ ] Audit current eval output — what does it look like today, where does it live, what fields exist
- [ ] Talk to Zeki about how eval runs are triggered and stored
- [ ] Sketch 2-3 dashboard variants: pass/fail trends, per-category breakdowns, failure case browser
- [ ] Decide on tooling — simple HTML? Streamlit? Internal web app? Something the team already runs?
- [ ] Mock first version with real data
- [ ] Review with Ken + Zeki
- [ ] Iterate

## Key Questions to Resolve

- **Audience:** Is this just for Ken's visibility, or is it also a team tool for regression catching?
- **Cadence:** One-shot on eval run, or live / refreshed dashboard?
- **Scope:** Single-model eval, or multi-model comparison?

## Notes

Ken's real want (reading between lines): *I don't want to read a 40-line log to know if Alfie is getting better.* The comprehensive dashboard should answer "is Alfie improving?" at a glance, with drill-down when he wants it.

Don't over-engineer on v1. The demo-dashboard style (single HTML page, fed by a JSON file) is probably right for the first cut.

## Outcomes / Results

*(fill in after shipping)*
