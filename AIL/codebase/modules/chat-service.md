---
type: codebase
tags: [module, chat, langgraph, supervisor, multi-agent, routing]
status: active
created: 2026-04-02
updated: 2026-04-02
related:
  - "[[AIL/codebase/modules/_index]]"
summary: "Core chat orchestration module — routes user messages through a LangGraph multi-agent supervisor to 14+ specialized agents (search, form filling, email, navigation, etc.)"
---

# Chat Service

## Purpose

The central orchestration layer for Alfie's chat interface. Receives a user message, enriches it with context (search results, chat history, memories, form state), routes it to the correct specialized agent via a LangGraph supervisor, and processes the response back to the user with sources, tables, and navigation actions.

## Inputs

- **User message** (text)
- **DB session** (SQLAlchemy)
- **client_id / user_id / chat_id** (auth context)
- **Optional**: page URL, screenshot, user images, document IDs, current time, timezone

## Outputs

```python
{
    "answer": str,           # Final formatted response
    "sources": list,         # Filtered document/news sources
    "query_type": str,       # MULTI_AGENT | FORM_FILLING | ERROR
    "agents_used": list,     # Which agents handled the request
    "chat_id": int,          # Persisted chat ID
    "message_id": int,       # Persisted message ID
    "comparison_table": dict, # Optional — markdown table + type
    "navigation_action": dict,# Optional — route for frontend nav
    "progress_history": list  # Optional — progress stage messages
}
```

## Key Files

| File | What It Does |
|------|-------------|
| `services/chat_service.py` | This module — supervisor creation, routing, response extraction |
| `services/chat_tools/` | All specialized agent tool implementations |
| `services/search_coordinator.py` | Pre-filters documents via fulltext search before agents run |
| `services/chat_history_service.py` | Loads/formats previous messages for context |
| `services/memory_service.py` | Fetches org + personal memories for LLM context |
| `services/notification_service.py` | Pushes real-time progress updates to frontend |
| `services/llm_service.py` | LLM abstraction (used for source filtering fallback) |
| `services/form_filling_service.py` | Core form filling logic (field extraction, conversation mgmt) |
| `static/chat_config.py` | Phrase lists for source-inclusion detection (intro, small talk, no-knowledge) |
| `models/chat_message.py` | DB model for individual messages |
| `models/user_chat.py` | DB model for chat sessions |

## How It Works

### Full Pipeline — Message to Response

#### 1. Constructor & Permission Check
`__init__` validates user access to the client via `DocumentService.check_user_permissions_for_client()`. Initializes two LLM models:
- **Fast model**: `ChatGroq` (gpt-oss-120b) — originally for supervisor routing (currently unused)
- **Prime model**: `ChatAnthropic` (claude-sonnet-4-6) — powers both supervisor and all agents

#### 2. Form Filling Pre-Check
**Before anything else**, checks if a form-filling session is active for this chat by calling `FormFillingTool.get_current_form_state_robust()` — queries the **database** (not just memory cache, critical for multi-worker environments like UAT). If active, sets `form_filling_active = True` and **skips all search coordination**.

#### 3. Search Coordination
If form filling is NOT active, determines whether to run a pre-search:
- **Short confirmations** ("yes", "no", "ok") → skip
- **Navigation/feedback/email keywords** → skip
- **User-selected documents** → force search
- **Everything else** → `SearchCoordinator.get_relevant_document_ids()`

The SearchCoordinator performs a **single fulltext search upfront** so agents don't redundantly search. Returns `ready_document_ids`, `is_preselected`, `is_fund_holding`, and counts.

#### 4. Context Injection for Tools
Class-level caches set up tool-specific contexts:
- `FeedbackTool` ← image context (screenshots, page URL)
- `NavigationTool` ← current page URL
- `EmailTool` ← selected document context
- `FormFillingTool` ← selected document context

#### 5. Chat History & Memory Loading
Previous messages loaded from DB via `ChatHistoryService`, converted to LangChain `HumanMessage`/`AIMessage`. Org + personal memories fetched via `MemoryService`.

#### 6. Context Message Assembly
Everything composed into a single rich context message containing: chat history, form filling context (if active), memory context, search context (pre-filtered doc IDs, counts, flags), and the actual user query with metadata.

#### 7. Routing — Two Paths

**Path A: Form Filling Direct Bypass**
If `form_filling_active` or `_is_form_filling_request(message)`, the system **completely bypasses the LLM supervisor** and calls `_handle_form_filling_directly()`. This is critical because user answers like "Apple Inc" would otherwise be routed to search agents. Supports: `exit`, `export`/`download`, and normal field answers. **Never returns None during active sessions.**

**Path B: LLM Supervisor Routing**
For all non-form messages, the LangGraph supervisor routes to exactly one agent. Created via `langgraph_supervisor.create_supervisor()` with a system prompt defining routing rules. `ToolRegistry.create_agents()` creates all specialized agents.

#### 8. Response Extraction
`_extract_final_response()` processes streamed chunks with priority:
1. Tool results (JSON with `status: success`)
2. Agent responses (last substantial message)
3. Supervisor direct responses
4. Fallback formatted tool data

#### 9. Source Filtering
Sources extracted from `_search_results_cache`, then filtered:
1. **Inline citations** (`<!-- SOURCES: [...] -->`) — deterministic
2. **"Found info from X documents"** claim — trusts AI count
3. **Table cell value matching**
4. **LLM-based filtering** (gpt-oss-120b fallback)

`_should_include_sources()` strips sources entirely for self-introductions, small talk, and no-knowledge responses.

#### 10. Storage & Cleanup
`store_chat_message()` persists to DB. `finally` block cleans all class-level caches (image, document, page URL, form filling, search, citations).

### Agent Routing Table

| Agent | Trigger | Purpose |
| --- | --- | --- |
| **General Search Agent** | Document content queries | Vector search on pre-filtered documents |
| **Fund Search Agent** | "What stocks does X hold?" | Fund holdings and investment search |
| **SelectedDocumentTool Agent** | User pre-selected docs | Operations on specific selected documents |
| **Comparison Agent** | "compare", "vs", "difference" | Side-by-side comparison tables |
| **Trend Agent** | "trend analysis", "trend table" | Time-based trend analysis |
| **News Agent** | "latest news", "market updates" | Financial news via external API |
| **System Agent** | "how many documents?" | System statistics, counts, metadata |
| **Fund Agent** | Fund info, client details | Fund information lookup |
| **Feedback Agent** | Complaints, frustration | Captures feedback, sends to team |
| **Email Agent** | "send email", "draft email" | Email composition and sending |
| **Form Filling Agent** | "fill form" | PDF form filling (backup; primary path is direct bypass) |
| **Memory Agent** | "remember my...", "forget..." | Save/delete personal and org memories |
| **Navigation Agent** | "go to", "navigate to" | Platform page navigation |
| **MCP Agents** | Dynamic from connected tools | External tool integrations (built dynamically) |

### Routing Priority Order
1. **Form filling** — absolute highest, locked mode
2. **Pre-selected documents** → Comparison / Trend / SelectedDocumentTool
3. **Keyword/intent matching** → appropriate specialized agent
4. **General knowledge** — supervisor answers directly, no agent

### Supervisor Safety Mechanisms
- `_preprocess_supervisor_input()` — injects aggressive override system messages when form mode detected
- `_validate_routing_in_chunk()` — real-time validation during streaming, checks `transfer_to_` tool calls
- `_analyze_message_for_routing_risks()` — detects search keywords, question patterns, entity names that could confuse routing during form filling

### Flow Diagram
```
User Message
    |
    +-- Permission check (constructor)
    +-- Form filling active? --- YES --> _handle_form_filling_directly() --> Store & Return
    |                            |
    |                            NO
    |                            |
    +-- SearchCoordinator (pre-filter documents)
    +-- Inject tool contexts (feedback, nav, email, form)
    +-- Load chat history + memory context
    +-- Assemble context message
    |
    +-- LangGraph Supervisor (Sonnet 4.6)
    |   +-- Routes to ONE specialized agent
    |   +-- Agent executes tools, returns response
    |   +-- Streams chunks with real-time routing validation
    |
    +-- Extract final response (prioritized)
    +-- Extract & filter sources (inline citations > claim count > LLM filter)
    +-- Extract tables & navigation actions
    +-- Store to database
    +-- Cleanup caches
```

## Dependencies

### Upstream (feeds into this)
- `SearchCoordinator` — provides pre-filtered document IDs
- `ChatHistoryService` — provides conversation context
- `MemoryService` — provides org + personal memories
- `FormFillingService` / `FormFillingTool` — form state management
- `DocumentService` — permission checks, S3 access
- `ToolRegistry` / `chat_tools/*` — all agent tool implementations
- `LLMService` — source filtering fallback (gpt-oss-120b)
- LangChain/LangGraph (`langgraph_supervisor`, `ChatAnthropic`, `ChatGroq`)

### Downstream (this feeds into)
- Frontend chat UI (via API response + `NotificationService` progress events)
- Database (`UserChat`, `ChatMessage` tables)
- `BaseTool._progress_messages` (consumed for progress history in response)

## Prompts Used

- **Supervisor system prompt** — massive inline prompt in `_create_supervisor()` defining all agent descriptions, routing rules, security rules, formatting rules, and memory handling guidelines
- **Source filtering prompt** — inline in `_filter_sources_by_answer()`, asks gpt-oss-120b to identify which sources are referenced in the answer
- **Form filling override prompt** — injected by `_preprocess_supervisor_input()` when form mode is active

## Implications of Change

<!-- THE KEY SECTION. What breaks or needs updating if you modify this module? -->

- **Adding a new agent**: Must update `ToolRegistry.create_agents()`, the supervisor system prompt routing rules in `_create_supervisor()`, and `_extract_agents_used()` agent name list
- **Changing LLM models**: Both `fast_model` and `prime_model` are initialized in `__init__`; the prime model is passed to all agents
- **Modifying search coordination**: `SearchCoordinator` results flow into the context message and `_search_context_cache`; agents depend on pre-filtered doc IDs
- **Form filling changes**: Extremely sensitive — the direct bypass path, DB state persistence, and supervisor override prompts all must stay in sync; form state is stored in both DB and memory cache
- **Source filtering logic**: 4-tier priority system; changing inline citation format breaks deterministic matching
- **Response formatting**: `_fix_response_formatting()` and `_fix_email_draft_formatting()` use regex that could mangle URLs if placeholder logic breaks
- **Class-level caches** (`_search_context_cache`, `_search_results_cache`, `_inline_citations_cache`): Shared state — concurrency issues possible if cleanup in `finally` block fails

## Open Questions

- The `fast_model` (Groq/gpt-oss-120b) is initialized but not used for supervisor routing — was this intentional or a regression?
- Form filling safety has extremely heavy prompt injection to force routing — is there a more reliable programmatic approach?
- `_search_results_cache` is class-level (shared across instances) keyed by `client_id_user_id` — could this collide in concurrent requests for the same user?
