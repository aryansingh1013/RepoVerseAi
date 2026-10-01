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

### 0. Local LLM (primary — no API keys needed)
RepoVerse is local-first: skills and chat run on **Ollama / Qwen3:8B** by default.
```bash
ollama serve
ollama pull qwen3:8b
ollama list
```

### 1. Setup Backend
Create a `.env` file inside `backend/.env`:
```env
HOST=0.0.0.0
PORT=8000

# Local-first LLM (defaults shown; override only if needed)
OLLAMA_ENDPOINT=http://localhost:11434/v1
OLLAMA_DEFAULT_MODEL=qwen3:8b
OLLAMA_TIMEOUT=600

# Optional cloud fallbacks (leave empty to stay fully local)
GROQ_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
HF_TOKEN=
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

## ⚙️ LLM Configuration

| Environment Variable | Description |
|---|---|
| `OLLAMA_ENDPOINT` | Local Ollama OpenAI-compatible endpoint (default `http://localhost:11434/v1`) |
| `OLLAMA_DEFAULT_MODEL` | Primary local model (default `qwen3:8b`) |
| `OLLAMA_TIMEOUT` | Local generation timeout in seconds (default `600` — CPU inference is slow) |
| `GROQ_API_KEY` | Optional cloud fallback (current production models: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`) |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` | Optional cloud fallbacks |

Skills documentation (what each skill does, universe isolation, testing): see [docs/SKILLS.md](docs/SKILLS.md).

---

## 🛠️ Technology Stack

- **Frontend**: React, TypeScript, Three.js / React Three Fiber, TailwindCSS
- **Backend**: FastAPI, LangGraph, LangChain, ChromaDB (Vector Store), BM25
- **Deployments**: Docker, Render configurations
