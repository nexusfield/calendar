
# Architectural Patterns

  

## Internal API: Router → Service → Model (Clean Architecture)

  

The `internal-api` follows a three-layer pattern:

1. **Router** (`api/*_router.py`) - HTTP endpoint, request validation, auth checks

2. **Service** (`services/*_service.py`) - Business logic, orchestration

3. **Model** (`models/*.py`) - SQLAlchemy ORM + Pydantic schemas in same file

  

Example chain:

- Router: `backends/internal-api/api/documents_router.py` (defines endpoints, calls service)

- Service: `backends/internal-api/services/document_service.py` (business logic)

- Model: `backends/internal-api/models/document.py` (ORM model + Pydantic response schemas)

  

Services are instantiated per-request in routers, receiving the DB session:

- See `backends/internal-api/api/dependencies.py:20` (`with_session()` generator)

  

## Internal API: FastAPI Dependency Injection

  

Auth and DB sessions are injected via `Depends()`:

- `get_db()` - DB session generator: `backends/internal-api/database.py:24`

- `get_current_user()` - JWT decode + user lookup: `backends/internal-api/api/dependencies.py:31`

- `get_current_user_with_client()` - User + client context: `backends/internal-api/api/auth_router.py:299`

- `oauth2_scheme` - Bearer token extraction: `backends/internal-api/api/dependencies.py:28`

  

## Internal API: Router Registration

  

All routers are registered under `/api` prefix in a single location:

- `backends/internal-api/main.py:134` (`app.include_router(router, prefix="/api")`)

- Routers are collected in `backends/internal-api/api/__init__.py`

  

## Internal API: Chat Tool System (Plugin Architecture)

  

Chat tools use an abstract base class + auto-discovery registry:

- **Base class**: `backends/internal-api/services/chat_tools/base_tool.py:10` (`BaseTool`)

- **Registry**: `backends/internal-api/services/chat_tools/tool_registry.py:11` (`ToolRegistry` - singleton)

- **Auto-discovery**: Registry scans `services/chat_tools/` for classes inheriting `BaseTool` (line 40-68)

  

To add a new chat tool:

1. Create `services/chat_tools/your_tool.py`

2. Inherit from `BaseTool`, implement `name`, `description`, `get_functions()`, `create_agent()`

3. The registry auto-discovers it - no manual registration needed

  

Existing tools: `SearchTool`, `FundTool`, `EmailTool`, `FormFillingTool`, `NewsTool`, `ComparisonTool`, `TrendTool`, `SystemTool`, `FeedbackTool`, `ClientTool`, `GeneralSearchTool`, `FundSearchTool`, `SelectedDocumentTool`

  

Each tool creates a LangGraph `react_agent` via `_create_agent_with_functions()`: `base_tool.py:103`

  

## Internal API: LangGraph Multi-Agent Architecture

  

Chat uses a supervisor pattern with LangGraph:

- Main orchestration: `backends/internal-api/services/chat_service.py`

- Each `BaseTool` creates its own agent via `create_agent()` method

- Supervisor routes user queries to appropriate tool agents

  

## Document Collect: Celery Task Worker

  

Browser automation service using Celery + Redis for distributed task processing:

- **Task definitions**: `backends/document-collect/tasks/document_collect_tasks.py`

- **Core logic**: `backends/document-collect/browser_use_impl.py` (`CollectorService`)

- **Config**: `backends/document-collect/celeryconfig.py` (Redis broker, thread pool, beat schedule)

  

Pattern: Internal API sends Celery task → worker picks up → `CollectorService` runs AI-powered browser agent → downloads documents. Periodic `check_overdue_sources` task runs every minute via Celery Beat.

  

## Lambdas: Event-Driven Serverless Handlers

  

Each lambda is a standalone SAM project with its own `template.yaml`, dependencies, and handler:

  

| Lambda | Language | Trigger | Entry Point |

|--------|----------|---------|-------------|

| `audit-notification` | Node.js | CloudWatch cron (daily 9AM UTC) | `index.js:handler` |

| `email-processor` | Node.js | SQS ← SNS ← SES | `index.js:handler` |

| `pdf-preview-lambda` | Node.js | CloudFront Lambda@Edge | `index.js:handler` |

| `pdf2png` | Python (Docker) | HTTP API (POST /resize) | `lambda_function.py:lambda_handler` |

  

Pattern: Single handler function per lambda, no service layer. Each has SAM `template.yaml` for infrastructure, `scripts/` for local dev.

  

## Shared Folder Service: Simple FastAPI

  

Lightweight FastAPI service without the service layer pattern:

- **Entry point**: `backends/shared-folder-service/main.py`

- **Endpoints**: `GET /sharedFolder` (directory listing), `POST /generate-documents` (synthetic doc generation via Bedrock)

  

Pattern: Endpoints defined directly in `main.py` with inline logic. No router/service/model separation.

  

## Frontend: React Query + API Layer

  

All server data flows through a consistent pattern:

1. **API function** in `web-ui/src/hooks/queries/api.ts` (wraps Axios calls)

2. **Custom hook** in `web-ui/src/hooks/queries/use*.ts` (wraps `useQuery`/`useMutation`)

3. **Component** consumes the hook

  

Examples:

- `web-ui/src/hooks/queries/api.ts:13` (imports `axiosInstance`)

- `web-ui/src/hooks/queries/useDocuments.ts` (query hooks for documents)

- `web-ui/src/hooks/queries/useSettings.ts` (queries + mutations pattern)

  

Query config: staleTime=60s, refetchOnWindowFocus=false

- See `web-ui/src/providers/QueryProvider.tsx:4-11`

  

## Frontend: Zustand State Management

  

Client-side state uses Zustand stores in `web-ui/src/stores/`:

- `chatStore.ts:92` - Chat state with `devtools` + `persist` middleware (sessionStorage)

- `documentStore.ts:33` - Document selection/UI state with `devtools`

- `clientStore.ts:8` - Logo/branding state

- `restoringDocumentsStore.ts:22` - Recycle bin restoration tracking

  

Pattern: `create<StoreInterface>()()` with optional middleware composition.

Zustand is used only for client-side UI state; server state lives in React Query.

  

## Frontend: Axios Interceptors for Auth

  

Global auth handling via Axios interceptors:

- Token injection on every request: `web-ui/src/utils/axiosInstance.ts`

- 401 response → clear token + redirect to login

- 403 response → dispatch custom permission error event

  

## Frontend: Path Aliases

  

TypeScript path alias `@/` maps to `web-ui/src/`:

- Config: `web-ui/tsconfig.json` (paths section)

- Usage: `import { Button } from '@/components/ui/Button'`

  

## Frontend: Feature-Based Organization

  

Features are organized in two complementary locations:

- `web-ui/src/features/` - Feature-specific components with complex state/logic

- `web-ui/src/components/ui/` - Reusable UI components organized by domain

  

## Internal API: Soft Deletes

  

Models use `is_deleted` boolean flag instead of hard deletes.

Queries must filter `is_deleted == False` (or use service methods that do this).

  

## Internal API: DB Connection Pooling

  

Connection pool configured at `backends/internal-api/database.py:8-15`:

- pool_size=20, max_overflow=20, pool_recycle=3600s, pool_pre_ping=True

  

## Internal API: Pydantic Models Co-located with ORM

  

Pydantic request/response schemas are defined in the same file as their SQLAlchemy model.

- Example: `backends/internal-api/models/document_source.py` - `DocumentSource` (ORM) + `DocumentSourceResponse` (Pydantic) + `DocumentSourceCreateRequest` (Pydantic)

  

## Multi-Tenancy

  

All data is scoped by `client_id`. Services receive client context from auth dependencies.

Users can belong to multiple clients via `UserClient` model.

- Model: `backends/internal-api/models/user_client.py:19`

  

## File Naming Conventions

  

| Context | Convention | Example |

|---------|-----------|---------|

| Frontend components | PascalCase | `DocumentDialog.tsx`, `Button.tsx` |

| Frontend hooks | camelCase with `use` prefix | `useDocuments.ts`, `useChat.ts` |

| Frontend pages | kebab-case directories | `admin-tools/`, `portfolio-settings/` |

| Backend routers | snake_case with `_router` suffix | `documents_router.py` |

| Backend services | snake_case with `_service` suffix | `document_service.py` |

| Backend models | snake_case (file), PascalCase (class) | `document.py` → `class Document` |

| Backend tests | `test_` prefix | `test_chat_router.py` |