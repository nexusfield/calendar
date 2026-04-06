---
type: codebase
tags: [module, search, fulltext, optimization, pre-filter]
status: active
created: 2026-04-02
updated: 2026-04-02
related:
  - "[[AIL/codebase/modules/chat-service]]"
summary: "Performs a single upfront fulltext search so downstream agents don't redundantly search. Optimizes queries via LLM and filters to READY documents only."
---

# Search Coordinator

## Purpose

Solve one problem: **agents were all running their own fulltext searches**, which was slow and redundant. The SearchCoordinator runs **one search, once**, before any agent is invoked, and hands the pre-filtered document IDs downstream.

## The Core Idea

Think of it like a receptionist at a library. Instead of letting every researcher (agent) walk into the stacks and search independently, the receptionist takes the question, pulls relevant books off the shelf, and hands the same stack to whoever needs it. One trip to the shelves instead of five.

## How It Works — Three Steps

### 1. Decide Whether to Search at All

The coordinator is only called from `ChatService.chat()`, and only when the message actually needs document context. Three outcomes:

- **User pre-selected documents** → Skip search entirely. Return those exact document IDs with `is_preselected: True`. The user already told us what to look at.
- **Message needs document context** (most queries) → Run fulltext search.
- **Form filling / navigation / feedback / small talk** → ChatService never calls the coordinator at all.

### 2. Optimize the Query

Raw user questions make bad search terms. "Can you find capital calls from the last month?" contains filler words and a relative time reference. The coordinator calls an LLM (`gpt-oss-120b` via `LLMService`) to distill it:

> "Can you find capital calls from the last month?" → `"capital calls April 2026"`

The prompt gives the LLM today's date so it can resolve "last month", "Q1", "past quarter" into concrete terms. If the LLM call fails, a basic fallback strips common prefixes ("find", "show me", "search for") and punctuation.

It also does **document type detection** — if the query mentions a document type name that exists in the client's system (e.g., "capital call"), it adds that as a facet filter to narrow results.

### 3. Run One Fulltext Search

Calls `DocumentSearchService.search_documents()` with:
- The optimized search term
- Limit of 50 documents
- Fuzzy matching enabled
- No highlights or facets (we just need IDs, not display data)

From the results, it:
- Filters to **READY documents only** (excludes Processing, Error, etc.)
- Extracts document IDs into two lists: all found, and ready-only
- Gets the total document count in the index (for the "I looked through X documents" header)
- Caches the result keyed by `client_id:search_term` so identical queries don't re-search

## What It Returns

```python
{
    "status": "success",
    "document_ids": [...],          # All matching doc IDs
    "ready_document_ids": [...],    # Only READY status docs (what agents actually use)
    "fulltext_total": 1200,         # Total docs in the index
    "ready_count": 15,              # How many READY docs matched
    "search_term": "capital calls April 2026",  # The optimized term
    "is_preselected": False,        # True if user picked docs manually
    "is_fund_holding": False        # Set by ChatService, not here
}
```

This dict flows into the supervisor's context message and gets cached at `ChatService._search_context_cache` so any agent can access the pre-filtered IDs without searching again.

## Why It Exists

| Without SearchCoordinator | With SearchCoordinator |
|---|---|
| General Search Agent runs fulltext search | One search, shared results |
| Fund Search Agent runs fulltext search | Agents receive pre-filtered IDs |
| SelectedDocumentTool runs fulltext search | No redundant index hits |
| Each search optimizes the query independently | One LLM call for query optimization |
| ~3-5 fulltext searches per query | 1 fulltext search per query |

## Key Files

| File | What It Does |
|------|-------------|
| `services/search_coordinator.py` | This module |
| `services/document_search_service.py` | Actual fulltext search engine (Elasticsearch/similar) |
| `services/llm_service.py` | Query optimization LLM call (`gpt-oss-120b`) |
| `services/document_type_service.py` | Document type lookup for facet filtering |
| `models/document_search_models.py` | `SearchRequest` data model |
| `models/document.py` | `DocumentStatus` enum (READY, Processing, Error) |

## Dependencies

### Upstream (feeds into this)
- `ChatService.chat()` — sole caller
- `DocumentSearchService` — performs the actual fulltext search
- `LLMService` — query optimization
- `DocumentTypeService` — document type detection for facet filters

### Downstream (this feeds into)
- `ChatService._search_context_cache` — all agents read from this
- Supervisor context message — `ready_document_ids` passed as search context
- The "I looked through X documents" response header uses `fulltext_total`

## Implications of Change

- **Changing search limits** (currently 50): Affects how many documents agents can work with. Too low = missed results. Too high = slower + token bloat.
- **Query optimization prompt**: Changes here affect which documents get found. The LLM resolves time references, so prompt changes could break temporal queries.
- **Caching**: Currently per-instance (not shared across requests). If the coordinator gets reused across queries, stale cache could return wrong results.
- **READY filter**: If a new document status is added, documents in that status won't appear unless the filter is updated.

## Open Questions

- The `is_fund_holding` flag appears in the return dict from ChatService but is never set by SearchCoordinator itself — where does this classification actually happen?
- Cache is instance-level (`self._fulltext_cache`) but only one search runs per `chat()` call — is the cache ever actually hit?
