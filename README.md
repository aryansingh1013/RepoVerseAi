# 🌌 RepoVerse AI

> Explore, analyze, and interact with any codebase as a stunning 3D galaxy of planets and stars.

RepoVerse AI is an advanced workspace analysis tool that visualizes your codebase directory structures as interactive 3D solar systems. It integrates an autonomous RAG (Retrieval-Augmented Generation) agent using a 10-node LangGraph workflow to answer technical questions and run code analysis tasks with grounding verification.

---

## 📁 Repository Structure Map

The codebase is organized into clean, modular directories. Below is a map of the repository's components:

```text
SUMMERTRAININGPROJECT/
├── backend/                  # FastAPI Web Backend & AI Agent
│   ├── agent/                # LangGraph nodes, state machine, and routers
│   ├── core/                 # Server configs, themes, and environments
│   ├── llm/                  # Centralized LLM ModelRouter & providers
│   ├── mcp/                  # Model Context Protocol tools and registry
│   ├── parser/               # Static code AST analysis and chunk builders
│   ├── rag/                  # Hybrid retriever (Vector DB + BM25)
│   ├── skills/               # Analysis plugins (Security, timelines, health)
│   ├── app.py                # Main FastAPI router & websocket handlers
│   └── requirements.txt      # Backend Python dependencies
│
├── frontend/                 # React & Three.js 3D Web UI
│   ├── public/               # Static assets
│   ├── src/                  # React components & hooks
│   │   ├── components/       # Interface overlays and chatbot panels
│   │   ├── hooks/            # Navigation state and WebSocket manager
│   │   └── three/            # 3D Canvas, OrbitControls, and galaxy rendering
│   └── package.json          # Frontend dependencies
│
├── db/                       # Persistent local database (ChromaDB index)
├── docs/                     # User guides & project reports
├── app.py                    # Workspace root backend launcher script
├── Dockerfile                # Deployment container blueprint
├── render.yaml               # Render cloud deployment configurations
└── requirements.txt          # Shared Python dependencies
```

---

## ✨ Core Features

- **Galactic 3D Code Explorer** — Renders directories as Star Systems, files as Orbiting Planets, and code symbols (classes, functions) as Moons using Three.js.
- **Autonomous RAG Agent** — A 10-node LangGraph Cognitive orchestration workflow featuring:
  - Pure Python query intent classification
  - Dependency-based task decomposition and planning
  - Verification & Fact Checking node to check grounding against code contexts
- **Interactive Mission Control** — Streaming WebSocket chat panel for querying codebase functionalities.
- **Guardrails & Context Filtering** — Automatically flags off-topic queries (e.g. general recipes or general knowledge) as `"Out of context"`.
- **Extensible AI Skills** — Plugins to run targeted analysis reports on codebase security, architecture, dependencies, and health.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Setup Backend
Create a `.env` file inside `backend/.env` with your API keys:
```env
HOST=0.0.0.0
PORT=8000
WORKSPACE_DIR=c:/Users/Aryan Singh/OneDrive/Desktop/SUMMERTRAININGPROJECT

# LLM Providers (At least one is required)
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

Install dependencies and start the Uvicorn server:
```bash
# From workspace root
pip install -r requirements.txt
python app.py
```

### 2. Setup Frontend
Install Node dependencies and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
Open your browser and navigate to `http://localhost:5173`.

---

## ⚙️ Configurable API Secrets

| Environment Variable | Description |
|---|---|
| `GROQ_API_KEY` | Recommended primary LLM provider (using Llama-3.3-70b) |
| `OPENAI_API_KEY` | Optional fallback provider |
| `GEMINI_API_KEY` | Optional fallback provider |

## 🔐 Security Model

RepoVerse reads your filesystem and can run build/test commands, so the backend ships locked down:

| Control | Behavior |
|---|---|
| **CORS** | `allow_origins` is an allowlist, not `*`. Set `CORS_ORIGINS=https://your-frontend.example` (comma-separated) for hosted frontends. Default: the local Vite dev server. |
| **Trusted-client gate** | Mutating/admin endpoints (`/api/index`, `/api/clone`, `/api/workspace/select`, `/api/workspace/list_directories`, `/api/settings`, `/api/mcp/config`) are restricted. **Localhost always allowed** (desktop use). Remote callers must set `REPOVERSE_ADMIN_TOKEN` on the server and send it as the `X-RepoVerse-Admin` header. |
| **Proxy awareness** | Behind Render/Railway/nginx, set `REPOVERSE_TRUST_PROXY=1` so the gate honors `X-Forwarded-For` — otherwise every remote user appears as `127.0.0.1` and inherits local trust. |
| **Terminal tools** | `terminal_run` executes only an allowlist (`pytest`, `npm test/build/lint`, `npx tsc --noEmit`), parsed to argv with `shell=False` — operator chaining (`&&`, `;`, pipes) is rejected. The `python_execute` tool was **removed**. The `terminal_mcp` plugin is **disabled by default**; flip `"terminal_enabled": true` in `backend/mcp_settings.json` only on a local install. |
| **Path containment** | `/api/file` and all filesystem tools resolve with `realpath` + `commonpath`, blocking `..` traversal, symlink escapes, and sibling-prefix confusion. |
| **Git clone** | `https://`/`ssh://`/`git://` only (no `file://`, no `ext::`, no embedded credentials, no option-injection); target folder names are sanitized. `REPOVERSE_ALLOW_INSECURE_CLONES=1` re-enables plain `http://` for LAN git servers. |

> ⚠️ These are P0 hardening measures for a single-operator tool. Multi-user deployments still need per-user auth (Supabase Auth / P1 migration) before the data layer itself becomes tenant-safe.

---

## 🛠️ Technology Stack

- **Frontend**: React, TypeScript, Three.js / React Three Fiber, TailwindCSS
- **Backend**: FastAPI, LangGraph, LangChain, ChromaDB (Vector Store), BM25
- **Deployments**: Docker, Render configurations
