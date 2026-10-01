# RepoVerse AI — System Design

> Technical design document: modules, data flows, sequences, storage schema, and routing behavior.
> Companion documents: [ARCHITECTURE.md](ARCHITECTURE.md) (high-level architecture) · [report.md](report.md) (project report).

---

## 1. System Overview

RepoVerse AI is a **local-first, RAG-grounded repository assistant** with a 3D "universe" visualization. A FastAPI backend ingests, chunks, embeds and indexes a codebase; a LangGraph agent answers questions grounded in retrieved code; a React + Three.js frontend renders the repository as an interactive galaxy.

```
┌─────────────────────────────────────────────────────────────────────┐
│              FRONTEND  (React 18 + TS + Vite + Three.js)            │
│  LandingPage → IndexingScreen → Workspace (SpaceScene + Chat HUD)   │
│  http://localhost:5173 (dev) — served by FastAPI in production      │
└──────────────┬──────────────────────────────────▲──────────────────┘
               │ REST /api/* + auth JWT            │ WS /ws/chat (streaming)
┌──────────────▼──────────────────────────────────┴──────────────────┐
│                  BACKEND  (FastAPI, port 7860)                     │
│                                                                    │
│  ┌──────────── ingestion ────────────┐  ┌──── serving ──────────┐  │
│  │ clone/select → parser → chunker   │  │ LangGraph agent       │  │
│  │ → embeddings → ChromaDB + BM25    │  │ Hybrid RAG retriever  │  │
│  └───────────────────────────────────┘  │ Skills / MCP tools    │  │
│                                         └───────────────────────┘  │
│  ┌──────────────────── LLM Router (key rotation + failover) ─────┐  │
│  │ chat → Groq(gpt-oss-20b) → Ollama(qwen3:8b) → OpenAI → …      │  │
│  │ analysis/indexing → Ollama(qwen3:8b) → Groq → …               │  │
│  └────────────────────────────────────────────────────────────────┘  │
│  ┌────────── Supabase (auth + cloud persistence, Phase 1) ───────┐  │
│  │ GoTrue JWT auth · repositories · jobs · conversations tables   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Module map

| Module | Path | Responsibility |
|---|---|---|
| API server | `backend/app.py` | REST endpoints, WebSocket chat, static SPA, background tasks |
| Agent | `backend/agent/` | 10-node LangGraph graph: plan → retrieve → execute → reflect → verify |
| Parser | `backend/parser/` | Directory scan, AST-aware chunking, symbol analysis |
| RAG | `backend/rag/` | ChromaDB vector store, BM25 index, hybrid RRF retriever |
| LLM | `backend/llm/` | Task router, model router (failover), provider registry (key rotation), 6 providers |
| MCP | `backend/mcp/` + `backend/plugins/` | Tool servers: filesystem, github, git, browser, terminal |
| Skills | `backend/skills/` | 9 one-click analyses with Markdown export |
| Auth | `backend/auth/` + `backend/api/` + `backend/database/` | Supabase JWT verification, REST routes, repository/job persistence |
| Core | `backend/core/` | Settings (pydantic), active workspace, theme |
| Frontend 3D | `frontend/src/three/` | SpaceScene, procedural texture engine, orbit/camera rigs |
| Frontend UI | `frontend/src/components/`, `pages/`, `hooks/` | HUD, panels, auth, navigation state |

---

## 2. Design Principles

1. **Local-first** — sensitive code never has to leave the machine: Ollama `qwen3:8b` handles analysis; cloud LLMs are opt-in/fallback.
2. **Grounded answers only** — every chat answer must cite retrieved chunks; low retrieval confidence yields "Not Found" rather than hallucination.
3. **Failover everywhere** — providers, API keys, and embeddings each have an ordered fallback chain.
4. **Streaming transparency** — agent steps stream live over WebSocket; the user sees the reasoning trace.
5. **Zero-asset visuals** — all 3D textures are generated procedurally at runtime (canvas + value noise), no image downloads.
6. **Fail-soft startup** — each subsystem (parser, MCP, cloud routes) initializes in its own try/except so a failure never prevents the API from binding.

---

## 3. Data Flows & Sequences

### 3.1 Ingestion (clone → searchable index)

```
User pastes GitHub URL / picks local folder      [LandingPage]
        │ POST /api/clone {repo_url}  or  /api/workspace/select {path}
        ▼
Background task starts; status = "cloning"        [app.py]
        │ git clone --depth 1 <url> (subprocess, timeout-guarded)
        │   (git pull fast-path if already cloned)
        ▼
Set active workspace → core/active_workspace.json [core/config.py]
        │ status = "indexing"
        ▼
Scan tree (allow-list ext, exclude .git/node_modules/…, ≤150 KB)
        ▼
ChunkBuilder (per file)                           [parser/chunk_builder.py]
   AST symbols (functions/classes) → "symbol" chunks
   non-symbol regions             → "global_block" chunks
   docs/json/text                 → "text_block" chunks
   every file                     → synthetic "file_summary" chunk
   oversized symbols → RecursiveCharacterTextSplitter (1000/200)
        ▼
EmbeddingsManager chain:                          [rag/embeddings.py]
   HF Inference API (bge-small-en-v1.5)
     → Gemini text-embedding-004
       → local SentenceTransformer (always works offline)
        ▼
ChromaDB persistent store (one collection per workspace hash, cosine HNSW)
        ▼
BM25 corpus fit (in-memory) + heuristics repo summary
        ▼
status = "ready" → frontend polls /api/workspace/status → fly into galaxy
```

### 3.2 Chat (WebSocket, streaming)

```
Client connects  ws://localhost:7860/ws/chat?token=<JWT>
        │ sends plain-text question
        ▼
LangGraph graph execution (backend/agent/graph.py):
   1 intent_classifier   — out-of-context? → END ("Not Found")
   2 goal_analyzer       — infer goal + metadata            ┐
   3 task_decomposer     — split into subtasks              │ reflection
   4 planner_v2          — order + tool assignment          │ can send
   5 retriever           — hybrid RAG (vector + BM25, RRF)  │ back to
   6 executor            — run tools/LLM calls in parallel  │ decomposer
   7 result_fusion       — merge tool + context results     │ (≤ 2 retries)
   8 reflection          — self-critique of draft           ┘
   9 generator           — grounded answer with citations
  10 verify              — fact-check citations; fail → re-enter at 2
        │ each node emits {type:"step", …} frame
        ▼
Frames streamed back:
  step → response → citations → confidence → goal_metadata
       → tasks_metadata → reasoning_trace → reflection_status → done
```

### 3.3 LLM call routing (every model call in the system)

```
model_router.generate(task, messages)              [llm/model_router.py]
        │
        ├─ task_router.resolve_task(task) → (provider, model)
        │     chat            → ("groq",   "openai/gpt-oss-20b")
        │     analysis, tool_selection, repository_summary,
        │     code_review, architecture_summary, offline
        │                     → ("ollama", "qwen3:8b")
        │
        ├─ build fallback chain:
        │     chain = fallback_order rotated to start at primary
        │     POLICY: if primary ≠ ollama, ollama is moved to position 1
        │     (chat: groq → ollama → openai → gemini → openrouter → hf)
        │
        └─ for each provider:
             skip if credentials required and no keys registered
             for each key (round-robin rotation, health-marked):
                 call provider → success? return response
                 429/rate-limit → mark key, next key
             all keys failed → telemetry fallback_event → next provider
          all providers failed → LLMResponse(status="failed")
```

Sources of keys (merged at startup): `backend/llm/config/provider_config.yaml` (`keys: [...]`) and environment variables — **multiple keys per provider are supported as a comma-separated list** (e.g. `GROQ_API_KEY=key1,key2`).

### 3.4 Skill execution

```
POST /api/skills/execute/{slug}
        │ skill_manager runs AST/regex analysis (local, no LLM)
        ▼
LLM synthesis via model_router (task="analysis" → qwen3:8b)
        │ JSON-mode generation, structured schema validation
        ▼
result cached per-workspace on disk
POST /api/skills/export/{slug} → Markdown report download
```

Error codes surfaced instead of masked: `OLLAMA_UNAVAILABLE`, `MODEL_MISSING`, `JSON_PARSE_FAILED`, `NO_UNIVERSE_SELECTED`, `WORKSPACE_NOT_FOUND`.

---

## 4. Storage Schema

| Store | Location | Schema / Content |
|---|---|---|
| ChromaDB | `db/chroma/` | one collection per workspace hash; documents = chunks; metadata: `path, language, class, function, imports, exports, summary, chunk_type, start_line, end_line` |
| BM25 | in-memory | tokenized chunk corpus keyed `path#chunk_type#start_line` |
| Active workspace | `backend/core/active_workspace.json` | `{ "active_workspace": "<abs path>" }` |
| MCP settings | `backend/mcp_settings.json` | server registry, timeouts, terminal safe-mode, GitHub token (never returned to client) |
| LLM routing | `backend/llm/config/*.yaml` | `model_config.yaml` (task → provider/model), `provider_config.yaml` (keys, rotation, fallback order) |
| Telemetry | in-memory | requests/failures/rate-limits/fallbacks/latency + fallback chain audit log |
| Supabase (cloud) | hosted Postgres | `repositories`, `jobs`, `conversations` — user-scoped via RLS; JWT verified server-side |
| Auth session | browser localStorage (`repoverse-auth`) | Supabase session, auto-refreshed |
| Workspace status | in-memory dict | `ready / cloning / indexing / error` + message |

---

## 5. Interface Contracts

### REST (selected)

| Method & Path | Request | Response (abridged) |
|---|---|---|
| `GET /api/workspace/status` | — | `{status, repo_name, error_message, current_path}` |
| `POST /api/index` | — | starts background indexing; poll status |
| `POST /api/clone` | `{repo_url}` | starts background clone+index |
| `POST /api/workspace/select` | `{path}` | switches universe, indexes in background |
| `GET /api/file?path=` | — | file content + analyzed symbols/imports/exports (path-traversal guarded) |
| `POST /api/settings` | partial settings | persisted to YAML, applied without restart |
| `GET /api/llm/telemetry` | — | counters + fallback chain log |
| `POST /api/auth/register` | `{email, password}` | 201 created (admin-confirmed) / 409 exists |
| `GET /api/skills` | — | skill registry listing |

### WebSocket `/ws/chat`

- **Send**: `{ query: string }`
- **Receive (ordered)**: `step` (one per agent node) → `response` → `citations[]` → `confidence` → `goal_metadata` → `tasks_metadata` → `reasoning_trace` → `reflection_status` → `done` | `error`
- **Auth**: JWT passed as `?token=` query param (browsers cannot set WS headers).

### Frontend ↔ Backend config

- `frontend/.env.local` → `VITE_API_URL=http://localhost:7860`, `VITE_WS_URL=ws://localhost:7860`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (publishable key only).
- Backend secrets (service key, LLM keys) live in `backend/.env` and are **never** exposed to the frontend.

---

## 6. Visualization Design (3D universe)

**Hierarchy mapping:** galaxy = repository · star = folder · planet = file · moon = function/class.

- `SpaceScene.tsx` — canvas root: lighting, fog, nebulae, starfield, body composition, OrbitControls + CameraRig (eased focus fly-to per depth: galaxy 15 · star 5.5 · planet 2.2 · moon 0.85).
- `OrbitingBody.tsx` — orbiting bodies (nested groups: moons orbit planets, planets orbit stars, stars orbit the galaxy core). Spheres only; per-kind procedural textures; glow sprites; optional ring systems.
- `FocusBody.tsx` — the focused body at origin, rendered large with full-detail textures (512–1024 px), pulsing corona for stars/galaxies.
- `textures.ts` — **procedural texture engine** (no image assets): tileable multi-octave value noise driving planet terrain (continents, bands, polar caps, craters), moon regolith (marè, crater rims, ray systems), star plasma granulation + sunspots, spiral-galaxy disc (core bulge, arms, dust lanes, star clusters), turbulent nebula sprites, ring banding with Cassini-style gaps. Orbit-view textures 256 px, focus-view 512–1024 px, all memoized per body.
- `positionsRegistry` — shared world-position store so HUD overlays can point at moving bodies.

---

## 7. Failure Handling Matrix

| Failure | Detection | Behavior |
|---|---|---|
| LLM key dead / rate-limited | non-success LLMResponse, "429" in error | mark key unhealthy → rotate to next key → next provider in chain |
| Groq down during chat | provider exhausted | chat falls back to **local qwen immediately** (ollama-first policy) |
| Ollama down during analysis | connection error to localhost:11434 | falls back to cloud chain (groq → openai → …) if keys exist |
| Ollama slow (CPU inference) | — | up to `OLLAMA_TIMEOUT` (default 600 s) before failover — slowness ≠ failure |
| Embedding API down | request exception | HF → Gemini → local SentenceTransformer chain |
| Out-of-context question | intent classifier | explicit "Not Found" answer instead of hallucination |
| Reflection/verify fail | self-critique node | re-plan / re-generate, ≤ 2 retries |
| Workspace missing on disk | status check | skill/chat error code `WORKSPACE_NOT_FOUND`, UI shows offline state |
| Path traversal attempt on `/api/file` | resolved-path containment check | 403 |
| Backend subsystem crash at boot | try/except wrappers | degraded but serving; warning printed |
| Frontend misconfigured (bad API URL) | health checks fail | landing page shows "Backend offline"; fix `.env.local` + restart Vite |

---

## 8. Performance Considerations

- **Embedding cache** — indexing is skipped when the Chroma collection already matches the current workspace (no re-embedding of unchanged repos).
- **File filters** — extension allow-list, excluded dirs, 150 KB size cap keep chunks relevant and indexing fast.
- **Texture budget** — 3D textures are generated once per body (`useMemo`), sized by view distance; additive-blended sprites instead of mesh postprocessing keep GPU cost low.
- **Streaming** — WebSocket frames arrive per agent step, so the UI feels live even while later nodes run.
- **Background tasks** — clone/index run in FastAPI background tasks; API stays responsive.
- **Bundle** — production build ~1.4 MB minified (Three.js dominates); code-splitting is a known future optimization.

---

## 9. Deployment Topology

| Mode | How | Notes |
|---|---|---|
| Dev (local) | `start_dev.bat` → uvicorn :7860 + Vite :5173 | two windows; frontend proxies env `VITE_API_URL` |
| Single container | `Dockerfile` — FastAPI serves `frontend/dist` SPA | one port, no CORS needed |
| PaaS | `render.yaml` / `Procfile` / Railway | `PORT` env respected by `app.py` |

Env var matrix (backend): `SUPABASE_URL`, `SUPABASE_ANON_KEY|PUBLISHABLE_KEY`, `SUPABASE_SERVICE_KEY|SECRET_KEY`, `GROQ_API_KEY` (comma-separated list supported), `OPENAI_API_KEY`, `GEMINI_API_KEY`, `HF_TOKEN`, `OPENROUTER_API_KEY`, `OLLAMA_ENDPOINT`, `OLLAMA_DEFAULT_MODEL`, `OLLAMA_TIMEOUT`, `HOST`, `PORT`.
