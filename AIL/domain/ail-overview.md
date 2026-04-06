---
type: domain
tags: [domain, ail, company, product, alfie]
created: 2026-04-03
updated: 2026-04-03
summary: "What Alpha Intelligence Labs is, what Alfie does, the market they're in, and the team behind it."
---

# Alpha Intelligence Labs — Company Overview

## What It Is

An AI platform built specifically for **institutional investment offices** — pension funds, endowments, sovereign wealth funds, family offices — that allocate heavily to alternative and private assets.

Incorporated in Delaware, October 2024. Operating out of Palo Alto. Currently in **stealth** — single landing page, no public product, active technical hiring.

## The Problem They're Solving

See: [[AIL/domain/private-markets-problem|Private Markets Problem]]

Private market information is unstructured, fragmented, and slow. There is no Bloomberg terminal for alternatives. Institutional LPs get quarterly letters 45 days after quarter-end, capital call notices, fund newsletters — all in PDF and prose, none plugging into any system. No standardized format. No aggregated view. No real-time signal.

## The Product — Alfie

Their AI chatbot superagent. Aggregates unstructured private market information (investor letters, fund updates, private company communications), ingests it with AI, and surfaces insights in real time.

The framing is **AI analyst**, not database — not just storing data, but understanding it and making it actionable.

**Competitive positioning:** Existing tools (Allvue, Cobalt, iLevel) are data management and reporting tools. AIL is positioning as the **intelligence layer above** that.

### Data Intake Architecture — 4 Layers

| Layer | What It Covers |
|-------|---------------|
| System layer | Broad functions universal to all users |
| Organizational layer | Institution-specific context |
| Personal layer | Individual user's documents, portfolios, positions |
| Core services layer | Details unclear — flagged to clarify with Ken |

### Long-Term Vision

Specialized agents per role — CIO agent, analyst agent, intern agent — filling gaps when humans aren't available.

## The Team

| Person | Role | Background |
|--------|------|------------|
| Ken Akoundi | CEO & Founder | RiskMetrics (JPMorgan), Deutsche Bank, Cordatius. 25+ years in this exact problem. |
| Zeki Mokhtarzada | CTO & Co-Founder | Webs ($117.5M), Truebill/RocketMoney ($1.275B) |
| Bobby Yazdani | Board Director / Early Backer | Saba Software ($1.3B), Cota Capital, #1 US angel investor (CB Insights 2014) |
| Devon | Head of Product | |

## Why It Matters for Alfie

This context is the foundation for everything Alfie does. Alfie's users are institutional analysts and CIOs. Their problems are information lag, unstructured data, and no aggregated view. Every prompt refinement, agent decision, and output analysis should be evaluated through this lens: **does this make it faster and easier for an investment professional to get signal from noise?**

## Related

- [[AIL/domain/private-markets-problem|Private Markets Problem]]
- [[AIL/domain/liquidation-preference|Liquidation Preference]]
- [[AIL/codebase/modules/chat-service|Chat Service]]
- [[AIL/people/Ken Akoundi|Ken Akoundi]]
- [[AIL/people/Zeki|Zeki Mokhtarzada]]
- [[AIL/people/Bobby Yazdani|Bobby Yazdani]]
