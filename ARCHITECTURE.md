# RepoVerse AI — System Architecture & Design

> AI-powered GitHub Repository Assistant that indexes codebases with RAG, orchestrates answers with a LangGraph agent, and visualizes repositories as an interactive 3D "universe".
>
> Concept: **GitHub + ChatGPT + VSCode + Space Exploration**

---

## 1. Space Metaphor (Domain Model)

| Space Object | Represents |
|---|---|
| Universe | All repositories |
| Galaxy | Repository |
| Star | Folder |
| Planet | File |
| Moon | Function / Class |

---

## 2. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Three.js)                 │
│  LandingPage → IndexingScreen → Workspace (3D Galaxy + Chat HUD)   │
└───────────────▲────────────────────────────────────▲───────────────┘
                │ REST (HTTP)                        │ WebSocket /ws/chat
┌───────────────┴────────────────────────────────────┴───────────────┐
│                     BACKEND API (FastAPI + Uvicorn)                │
│                                                                    │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────────────────┐  │
│  │ Parser   │──▶│ RAG Pipeline │──▶│ LangGraph Agent (10 nodes) │  │
│  │ Chunker  │   │ Hybrid       │   │ Plan → Retrieve → Execute  │  │
│  │ Analyzer │   │ Retriever    │   │ → Reflect → Verify         │  │
│  └──────────┘   └──────┬───────┘   └──────────┬─────────────────┘  │
│                        │                      │                    │
│                 ┌──────▼───────┐      ┌───────▼─────────────────┐  │
│                 │  ChromaDB    │      │  LLM Router (multi-     │  │
│                 │  + BM25      │      │  provider + fallback)   │  │
│                 └──────────────┘      └───────┬─────────────────┘  │
│                                               │                    │
│  ┌────────────────────────────────────────────▼─────────────────┐  │
│  │              MCP Layer (registry + connection manager)       │  │
│  │   filesystem · github · git · browser · terminal (plugins)   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
                │
     ┌──────────┼─────────────┬──────────────┬──────────────┐
     ▼          ▼             ▼              ▼              ▼
   Groq      OpenAI        Gemini        OpenRouter      Ollama
  (LLM)      (LLM)      (LLM+Embed)        (LLM)         (local LLM)
              Hugging Face Inference API (Embeddings)
```

### Runtime layers

1. **API Layer** — `backend/app.py` (FastAPI): REST endpoints, WebSocket chat, static SPA serving, background task orchestration (clone/index).
2. **Agent Layer** — `backend/agent/`: LangGraph cognitive workflow, planner, task decomposer, parallel executor, reflection, permissions, execution memory.
3. **RAG Layer** — `backend/rag/`: vector store (Chroma), BM25 index, hybrid retriever with Reciprocal Rank Fusion.
4. **Parser Layer** — `backend/parser/`: galaxy parser (directory tree), chunk builder (AST-aware), code analyzer (symbols/imports/exports).
5. **LLM Layer** — `backend/llm/`: model router, task router, provider router with key rotation, fallback order, and telemetry; providers for Groq/OpenAI/Gemini/HF/OpenRouter/Ollama.
6. **MCP Layer** — `backend/mcp/` + `backend/plugins/`: Model Context Protocol servers registry, dynamic tool loader, connection manager with health checks.
7. **Skills Layer** — `backend/skills/`: one-click analysis reports (security, performance, README generation, etc.).
8. **Core** — `backend/core/`: settings (`pydantic-settings`), active workspace persistence, theme config.
9. **Frontend** — `frontend/`: React 18 + TypeScript + Vite + Three.js (react-three-fiber) 3D visualization, Tailwind, Framer Motion.

---

## 3. System Design

### 3.1 Repository Ingestion Flow

```
User (GitHub URL / local folder)
        │
        ▼
POST /api/clone or /api/workspace/select   (background task)
        │
        ▼
git clone / git pull (subprocess, timeout-guarded)
        │
        ▼
Set active workspace (persisted to core/active_workspace.json)
        │
        ▼
POST /api/index  →  scan workspace
   • allow-list of source extensions (.py .ts .tsx .js .md .yaml …)
   • exclude dirs (.git, node_modules, venv, dist …) & lock files
   • skip files > 150 KB (binaries/generated)
        │
        ▼
ChunkBuilder (AST-aware, per-file)
   • symbol chunks (functions/classes = Moons)
   • orphan global blocks
   • file_summary chunk (Planet entry point)
        │
        ▼
EmbeddingsManager (HF API → Gemini → local SentenceTransformer fallback)
        │
        ▼
ChromaDB (persistent, cosine HNSW, per-workspace collection)
        │
        ▼
BM25 index fit (in-memory) + heuristics repo summary → Ready
```

### 3.2 Chat / Agent Flow (LangGraph)

10-node cognitive graph (`backend/agent/graph.py`):

```
intent_classifier ──(out of context → END)
        │
        ▼
  goal_analyzer ──────────────┐
        ▼                     ▲ (verify failed → retry ≤ 2)
  task_decomposer ◀───────────┤ (reflection → re-plan, retry ≤ 2)
        ▼                     │
   planner_v2                 │
        ▼                     │
    retriever (Hybrid RAG)    │
        ▼                     │
   executor (parallel)        │
        ▼                     │
  result_fusion               │
        ▼                     │
    reflection ───────────────┘
        ▼
    generator (LLM, grounded answer)
        ▼
     verify (fact-check citations)
        ▼
       END
```

- **State** (`AgentState`): query, retrieved contexts, tool outputs, agent steps, citations, confidence score, retries, reasoning trace, goal/tasks metadata, reflection status.
- **Guardrails**: max 2 retries per loop; "Not Found" answer when retrieval confidence is low; every answer must cite source files.
- **Streaming**: the WebSocket handler streams each agent step live (`type: step`), then `response`, `citations`, `confidence`, `goal_metadata`, `tasks_metadata`, `reasoning_trace`, `reflection_status`, `done`.

### 3.3 Hybrid Retrieval (RAG)

- **Dense**: ChromaDB vector search with cosine similarity over embeddings of `BAAI/bge-small-en-v1.5` (fallback `all-MiniLM-L6-v2`).
- **Sparse**: in-memory BM25 lexical index (`backend/rag/bm25_index.py`).
- **Fusion**: Reciprocal Rank Fusion — `score = 1/(60 + rank_vector) + 1/(60 + rank_bm25)` — keyed by `path#chunk_type#start_line`; supports metadata `where` filters on both channels.

### 3.4 Chunking Strategy (language-aware)

- AST symbol extraction for Python and JS/TS (via `CodeAnalyzer`): one chunk per function/class with line ranges.
- Large symbols sub-split with `RecursiveCharacterTextSplitter` (chunk 1000 / overlap 200).
- Non-symbol regions are captured as `global_block` chunks (config, setup code, comments).
- Docs/JSON/text files → generic `text_block` chunks.
- Every file gets a synthetic `file_summary` chunk (path, language, imports, exports, symbols).
- Metadata enrichment: `path`, `language`, `class`, `function`, `imports`, `exports`, `summary`, `chunk_type`, line range.

### 3.5 LLM Orchestration

- **Task router** maps tasks → (provider, model). Current routing policy: **`chat` → Groq (`openai/gpt-oss-20b`)** for fast replies; **all other tasks** (`analysis`, `tool_selection`, `repository_summary`, `code_review`, `architecture_summary`, `offline`) → **local Ollama `qwen3:8b`** so code analysis stays on-device.
- **Model router** walks a fallback order on failure/rate-limit. **Local-first failover policy:** when the primary is a cloud provider, `ollama` is moved to position 1 of the chain — e.g. chat falls back `groq → ollama(qwen) → openai → gemini → …`, so a dead Groq key degrades to local inference rather than another cloud.
- **Provider registry** supports **multiple API keys per provider** (comma-separated in `.env`, e.g. `GROQ_API_KEY=key1,key2`, or a list in `provider_config.yaml`) with `round_robin` rotation, per-key health marking, success/failure/rate-limit counters; dead keys are skipped automatically.
- **Telemetry**: requests, failures, rate limits, fallback events, average latency, fallback chain log — exposed via `/api/llm/telemetry`.
- **Slow ≠ down**: local generation gets a generous timeout (`OLLAMA_TIMEOUT`, default 600 s) so CPU inference speed never triggers premature cloud failover.
- **Embeddings fallback chain**: Hugging Face Inference API → Gemini `text-embedding-004` → local SentenceTransformer.

### 3.6 Skills (Phase 5)

Executable one-click analyses run through the skills layer and export Markdown reports:
`overview` (static), `architecture` (LLM), `health` (AST + LLM recs), `dependencies` (AST + cycle detection), `timeline` (git), `learning` (LLM), `readme` (LLM), `security` (regex + LLM summary), `performance` (AST + LLM insights).

All skills execute against the active universe (`settings.WORKSPACE_DIR`) with hard validation, per-workspace disk caching, and structured error codes on LLM failure (`OLLAMA_UNAVAILABLE`, `MODEL_MISSING`, `JSON_PARSE_FAILED`, …). Full reference: [docs/SKILLS.md](docs/SKILLS.md).

### 3.7 MCP (Model Context Protocol)

- `MCPServerRegistry` + `DynamicToolLoader` + `MCPConnectionManager` (health checks, status telemetry, config hot-reload).
- Built-in plugin servers: `filesystem`, `github`, `git`, `browser`, `terminal` (safe-mode option), plus a mock server.
- `AgentToolRegistry` exposes MCP tools to the agent executor; filesystem MCP root is rebound automatically when the workspace changes.
- Config persisted in `mcp_settings.json`; GitHub token never returned to the client.

### 3.8 Visualization Design

- `frontend/src/three/`: `SpaceScene` (canvas root), `FocusBody` (focused body), `OrbitingBody` (orbiting bodies, nested groups), `StarField`, `CameraRig`, `positionsRegistry` (shared node positions).
- **Procedural texture engine** (`frontend/src/three/textures.ts`): all surfaces are canvas-generated with tileable multi-octave value noise — planet terrain (continents, gas-giant bands, polar ice caps, lit craters), cratered moons (marè, bright rims, ray systems, relief bump maps), plasma stars (granulation, sunspots, emissive maps), spiral-galaxy disc (core bulge, arms, dust lanes, star clusters), turbulent nebula sprites, and ring banding with Cassini-style gaps. Zero image assets; orbit-view textures 256 px, focus-view 512–1024 px, memoized per body.
- File preview runs `CodeAnalyzer` on the backend to show language, symbols, imports, exports.
- HUD: `AIOrb` (chat), `NavigationHud`, `BottomStatusBar`; animations via Framer Motion; rule: animations must never reduce usability.

### 3.9 State & Persistence

| Item | Where |
|---|---|
| Active workspace path | `backend/core/active_workspace.json` |
| Vector store | `db/` (Chroma persistent client, one collection per workspace hash) |
| MCP settings | `backend/mcp_settings.json` |
| LLM task/provider configs | YAML files (written by `/api/settings`) |
| Repo summaries / BM25 corpus | in-memory (`indexed_data`) |
| Cloned repositories | `db/cloned_repos/<repo>` |
| Workspace status | in-memory dict (ready / cloning / indexing / error) |

### 3.11 Security Notes

- Path traversal protection on `/api/file` (resolved path must stay inside workspace).
- MCP config API strips `github_token` before responding.
- Terminal MCP safe-mode flag; index allow-list excludes `.env`, lock files, binaries.

---

## 4. Features

### Repository Ingestion
- Clone from GitHub URL (with `git pull` fast-path if repo already cloned)
- Select local folder (native OS dialog or web-based directory browser)
- Background clone/index with live status polling
- Smart filtering: allowed source extensions, excluded dirs/lock files, 150 KB size cap
- Embedding cache: skips re-embedding when the workspace hasn't changed

### AI Chat (Grounded Q&A)
- 10-node LangGraph agent with planning, parallel tool execution, reflection and fact-check loops
- Hybrid RAG answers with file/line citations and confidence score
- Out-of-context detection ("Not Found" instead of hallucination)
- Live streaming of the agent's reasoning steps over WebSocket
- Cognitive timeline: goal metadata, task breakdown, reasoning trace, reflection status

### Repository Visualization
- Interactive 3D universe (Three.js / react-three-fiber): galaxies, stars, planets, moons
- Camera rig with focus/follow on selected bodies
- File preview with analyzed symbols, imports, exports
- Navigation HUD + status bar; space theme config served from backend

### Skills & Reports
- One-click skill execution (security, performance, architecture, dependencies, health, git timeline, learning mode, README generation)
- Markdown report export per skill

### Operations & Settings
- Multi-provider LLM management: preferred provider/model, fallback order, rotation strategy — all editable at runtime via `/api/settings` (persisted to YAML, no restart needed)
- LLM telemetry dashboard (latency, failures, rate limits, key health)
- MCP dashboard: connection status telemetry, configurable filesystem root / terminal safe mode / timeouts
- Health endpoint; CORS enabled; single-container production mode (FastAPI serves built React SPA)

---

## 5. Tech Stack

### Backend
| Area | Technology |
|---|---|
| Language | Python |
| API framework | FastAPI + Uvicorn (`websockets` support) |
| Validation / config | Pydantic, pydantic-settings, python-dotenv |
| Orchestration | LangGraph (StateGraph) |
| RAG framework | LangChain, langchain-core, langchain-community, langchain-text-splitters |
| Vector DB | ChromaDB (persistent client, cosine HNSW) |
| Keyword search | Custom BM25 index (rank-bm25-style scoring) |
| Embeddings | Hugging Face Inference API, Gemini `text-embedding-004`, sentence-transformers |
| LLM SDKs | groq, openai, google-generativeai, httpx/requests |
| Git | git CLI via subprocess (gitpython available) |
| MCP | `mcp` package + custom registry/loader/connection manager |
| Config files | YAML (task & provider routing), JSON (workspace, MCP) |

### Frontend
| Area | Technology |
|---|---|
| Language | TypeScript |
| UI framework | React 18 |
| Build tool | Vite |
| 3D engine | Three.js + @react-three/fiber + @react-three/drei + three-stdlib |
| Animation | Framer Motion |
| Styling | Tailwind CSS + PostCSS + Autoprefixer |
| Routing | react-router-dom v6 |
| Icons | lucide-react |

### Deployment
| Item | Detail |
|---|---|
| Entry point | `app.py` → `backend.app:app` (port 7860 default for HF Spaces, `PORT` env override) |
| Containers | `Dockerfile`, `Procfile` |
| PaaS | `render.yaml` (Render blueprint) |
| Production mode | FastAPI mounts `frontend/dist` (`/assets` + SPA catch-all, API/WS routes excluded) |

---

## 6. API Reference

### Health & Theme
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health`, `/api/health` | Health check |
| GET | `/api/theme` | Space-theme configuration for the frontend |

### Repository & Indexing
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/scan` | Scan codebase tree structure |
| POST | `/api/index` | Index workspace into ChromaDB + BM25 (cached if unchanged) |
| GET | `/api/summary` | Precompiled heuristics repository summary |
| GET | `/api/file?path=` | File preview + static analysis (language, symbols, imports, exports) |

### Workspace Management
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/workspace/status` | Background task status (`ready`/`cloning`/`indexing`/`error`) |
| GET | `/api/workspace/browse` | Native OS folder picker dialog (Tkinter) |
| GET | `/api/workspace/list_directories?path=` | Web-based directory browser |
| POST | `/api/workspace/select` | Switch to a local folder, index in background |
| POST | `/api/clone` | Clone a GitHub repo URL, index in background |

### Auth & Cloud Persistence (Supabase — Phase 1)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/auth/me` | Current user from JWT |
| POST | `/api/auth/register` | Admin-backed signup (pre-confirmed, no email rate limits); 409 on duplicate |
| POST/GET/DELETE | `/api/repositories…` | Per-user repository records (RLS-scoped) |
| POST | `/api/repositories/{id}/index` | Kick off indexing job for a stored repo |
| GET | `/api/jobs/{job_id}` | Background job status |
| POST/GET | `/api/repositories/{id}/conversations` | Persisted chat conversations |
| POST/GET | `/api/conversations/{id}/messages` | Conversation messages |
| POST | `/api/conversations/{id}/citations` | Attach citations to a message |
| GET/PUT | `/api/user/settings` | Per-user settings |

Auth: Supabase GoTrue JWT issued on sign-in; frontend attaches `Authorization: Bearer` to REST and `?token=` on WebSocket; backend verifies against `SUPABASE_JWKS_URL`. Only the **publishable anon key** lives in the frontend (`VITE_SUPABASE_ANON_KEY`); the service key is backend-only.

### LLM & Settings
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/settings` | Update model/task routing, fallback order, embedding model (persisted to YAML) |
| GET | `/api/llm/telemetry` | Requests, failures, rate limits, latency, key health, fallback chain log |

### MCP
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/mcp/config` | Current MCP settings (token redacted) |
| POST | `/api/mcp/config` | Update settings + hot-reload connections |
| GET | `/api/mcp/dashboard` | MCP connection status telemetry |

### Skills
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/skills` | List available skills |
| POST | `/api/skills/execute/{slug}` | Run a skill through the agent graph |
| POST | `/api/skills/export/{slug}` | Export a skill result as Markdown report |

### Chat (WebSocket)
| Protocol | Endpoint | Messages received |
|---|---|---|
| WS | `/ws/chat` | Send: plain text query. Receive (JSON frames): `step` → `response` → `citations` → `confidence` → `goal_metadata` → `tasks_metadata` → `reasoning_trace` → `reflection_status` → `done` (or `error`) |

### Static / SPA (production)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/assets/*` | Built frontend assets |
| GET | `/`, `/{path}` | SPA entry (React Router); API/WS paths excluded |

### External APIs Consumed
| Provider | Usage |
|---|---|
| Groq API | Cloud fallback chat LLM (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`) |
| OpenAI API | Chat LLM provider |
| Google Gemini API | Cloud fallback chat LLM + embeddings (`text-embedding-004`) |
| Hugging Face Inference API | Embeddings (`BAAI/bge-small-en-v1.5`) |
| OpenRouter API | Chat LLM provider |
| Ollama (local) | **Primary local LLM** (`qwen3:8b`) — cloud only as configured fallback |
| GitHub | Repository cloning via `git clone`/`git pull`; metadata via GitHub MCP |

---

## 7. Techniques Used

| Technique | Where / How |
|---|---|
| **RAG (Retrieval-Augmented Generation)** | Every answer grounded in retrieved chunks with citations; retrieval-first policy |
| **Hybrid Search** | Dense (ChromaDB cosine) + sparse (BM25) retrieval |
| **Reciprocal Rank Fusion (RRF)** | Merges vector & BM25 result rankings with `1/(60+rank)` weighting |
| **AST-aware chunking** | Language-specific symbol extraction (functions/classes) instead of naive splitting |
| **Recursive text splitting** | LangChain `RecursiveCharacterTextSplitter` (1000 chars / 200 overlap) for oversized or non-code content |
| **Metadata enrichment** | Imports/exports/summary/symbols stored per chunk for filtered retrieval |
| **Embedding cache** | Skips re-embedding when the Chroma collection matches the current workspace |
| **Multi-provider fallback chain** | Ordered provider failover on errors/rate limits |
| **API key rotation** | Round-robin selection across multiple keys per provider with health tracking |
| **Task-based model routing** | Different (provider, model) pairs per task type |
| **Reflection (self-critique)** | Agent re-plans up to 2× when output quality is judged insufficient |
| **Verification / fact-checking** | Post-generation check node; failed checks re-enter analysis (≤ 2 retries) |
| **Goal decomposition & planning** | Goal analyzer → task decomposer → planner v2 before execution |
| **Parallel tool execution** | Executor fan-out over planned tasks with result fusion |
| **Agent state machine** | Typed `AgentState` threaded through the LangGraph graph |
| **Streaming agent traces** | WebSocket step-by-step execution log for UX transparency |
| **Heuristics summarization** | No-LLM structural repository summary (fast, free) |
| **MCP tool integration** | Standardized tool servers (filesystem, GitHub, git, browser, terminal) |
| **Path-traversal protection** | Resolved-path containment check for file reads |
| **Background task processing** | FastAPI `BackgroundTasks` for clone/index so the API stays responsive |
| **Per-workspace namespacing** | Chroma collection per workspace hash; embeddings isolated per repo |
| **Cosine similarity HNSW** | Approximate nearest neighbor search in ChromaDB |
| **LLM observability** | Telemetry counters, latency averages, fallback chain audit log |
| **Static analysis** | Symbol/import/export extraction powering file previews & summaries |

---

## 8. Project Structure

```
├── app.py                     # Uvicorn entry point (PORT env, default 7860)
├── backend/
│   ├── app.py                 # FastAPI: REST + WebSocket + static SPA
│   ├── core/                  # Settings, workspace persistence, theme
│   ├── parser/                # galaxy_parser, chunk_builder, code_analyzer
│   ├── rag/                   # vector_store, bm25_index, retriever (hybrid)
│   ├── agent/                 # graph, nodes, planner, executor, reflection…
│   ├── llm/                   # model/task/provider routers, providers/*
│   ├── mcp/                   # registry, loader, connection manager, config
│   ├── plugins/               # filesystem, github, git, browser, terminal MCP
│   └── skills/                # 9 analysis skills + registry + manager
├── frontend/
│   ├── src/pages/             # LandingPage, IndexingScreen, Workspace
│   ├── src/three/             # SpaceScene, textures (procedural engine), StarField, CameraRig…
│   ├── src/components/        # AIOrb, NavigationHud, BottomStatusBar…
│   └── package.json           # React 18 + Three.js + Vite stack
├── db/                        # ChromaDB storage + cloned_repos/
├── Dockerfile · Procfile · render.yaml
└── docs/ · prd.md · schema.md · appflow.md · implementation.md · rules.md
```
