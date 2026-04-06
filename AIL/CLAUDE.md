# CLAUDE.md — Vault Instructions for AI Instances

> This file tells any future Claude instance how to operate inside this vault. Read this first before doing anything else.

## What This Vault Is

Landon's personal knowledge base for his internship at **Alpha Intelligence Labs (AIL)**, built in Obsidian. It tracks people, codebase documentation, domain knowledge, daily work logs, and projects.

## Who Landon Is

Intern at AIL. Role: **prompt engineering and holistic output analysis on Alfie** — refining prompts, analyzing outputs across the platform. Reports primarily to Zeki (CTO), also takes direction from Ken (CEO). See `people/Landon.md`.

## Vault Structure

| Folder | What Goes Here |
|--------|---------------|
| `people/` | One note per person — teammates, managers, stakeholders |
| `codebase/` | Technical docs — modules, prompts, architecture decisions |
| `domain/` | Concepts Landon needs to understand: finance, startups, investing, product |
| `process/` | Workflows, conventions, how things work at AIL |
| `daily/` | Daily logs — one file per day, named `YYYY-MM-DD.md` |
| `projects/` | Active and past projects |
| `_templates/` | Obsidian templates — always use these as the base for new notes |

## Rules — Always Follow These

1. **State every file touched.** Every time you create or edit a file, tell the user the full path and filename. No exceptions.
2. **Use templates strictly.** Every new note must follow the corresponding template in `_templates/`. Check the template before creating any new file.
3. **Fill frontmatter completely.** Never leave `name`, `role`, `summary`, or `tags` blank if the information is known.
4. **Consistent Key Conversations format.** All person notes use a table for Key Conversations: `| Date | Topic | Notes |`
5. **Domain is broad.** Domain knowledge covers finance, institutional investing, startups, venture capital, product — not just finance.
6. **Daily notes follow the template exactly.** Must include `## Daily Meeting` with Problems Discussed table, Key Takeaways, My Work, Notes, Tasks.
7. **Don't invent information.** If something is unknown, leave it blank or flag it — don't guess.
8. **Cross-link liberally.** Use `[[AIL/path/to/note|Display Name]]` to connect related notes.

## Current Priorities (as of 2026-04-06)

1. ~~Get Docker running locally~~ — **Done**
2. ~~Connect Claude to GitHub repo~~ — **Done**
3. Meeting with Devon (Head of Product) — **Tuesday 4/7 at 12PM ET (11AM CST)**
4. Define what "make Alfie smarter" actually means — push back on Ken, identify concrete problems

## Key Context

- AIL is in **stealth** — no public product yet
- Alfie is the AI chatbot superagent — Landon's primary focus
- The codebase uses LangGraph, LangChain, Claude Sonnet 4.6, and Groq
- Zeki is ~70% Landon's boss day-to-day; Ken sets high-level direction
- See `domain/ail-overview.md` for full company/product context
