# RepoVerse AI — Project Report

> AI-powered GitHub Repository Assistant that indexes codebases with RAG, answers questions through a LangGraph agent, and visualizes repositories as an interactive 3D universe.
>
> **Concept: GitHub + ChatGPT + VSCode + Space Exploration**

---

## 1. Executive Summary

RepoVerse AI lets a developer point at any repository — a GitHub URL or a local folder — and get:

1. **A searchable knowledge base** of the code (hybrid RAG: vector + keyword search),
2. **A grounded chat assistant** that answers questions with file/line citations and streams its reasoning live,
3. **An explorable 3D universe** where the repository is a galaxy, folders are stars, files are planets, and functions/classes are moons,
4. **One-click analysis skills** — security, performance, architecture, dependency, health and timeline reports exported as Markdown.

The system is **local-first**: code analysis runs on a local Ollama model by default, so proprietary code never has to leave the machine, with cloud providers (Groq/OpenAI/Gemini/OpenRouter) as configurable fallback. It is deployed-ready as a single FastAPI container that also serves the built React frontend.

---

## 2. Problem Statement

Understanding an unfamiliar codebase is slow:

- Documentation is stale or missing; knowledge lives in senior devs' heads.
- Generic LLM chatbots hallucinate — they haven't read *your* code.
- Existing analyzers produce walls of metrics, not answers.
- Sending proprietary code to cloud AI is often unacceptable.

**RepoVerse AI's answer:** index the actual repository, ground every answer in retrieved code with citations, keep inference local by default, and make exploration visual and intuitive.

---

## 3. Objectives & Outcomes

| Objective | Outcome |
|---|---|
| Grounded Q&A over any repository | ✅ 10-node LangGraph agent; every answer cites source files; "Not Found" on out-of-context queries instead of hallucination |
| Fast, relevant retrieval | ✅ Hybrid dense (ChromaDB) + sparse (BM25) retrieval fused with Reciprocal Rank Fusion |
| Visual codebase exploration | ✅ Full 3D universe (Three.js): orbiting bodies, focus/follow camera, file preview with symbols |
| One-click repo intelligence | ✅ 9 skills with Markdown export (security, performance, architecture, dependencies, health, timeline, learning mode, README, overview) |
| Local-first, cost-controlled inference | ✅ Local qwen3:8b default for analysis; fast cloud Groq for chat; automatic failover between them |
| Production deployability | ✅ Single-container mode (FastAPI serves SPA), Railway/Render configs, Supabase cloud persistence |

---

## 4. Features Delivered

### 4.1 Repository Ingestion
- Clone from GitHub URL (fast-path `git pull` when already cloned) or select a local folder (native dialog or in-browser directory browser).
- Background indexing with live status polling (`cloning → indexing → ready`).
- Language-aware AST chunking (Python, JS/TS), recursive splitting for oversized symbols, metadata enrichment (imports, exports, symbols, line ranges).
- Smart filtering: extension allow-list, excluded dirs, 150 KB size cap; embedding cache skips unchanged workspaces.

### 4.2 Grounded AI Chat
- Streaming WebSocket chat with live agent-step trace (plan → retrieve → execute → reflect → verify).
- Hybrid RAG with file/line citations and a confidence score.
- Self-critique loop: reflection re-plans up to 2×; verification fact-checks citations.
- Cognitive timeline UI: goal metadata, task breakdown, reasoning trace.

### 4.3 3D Universe Visualization
- Galaxy = repository, star = folder, planet = file, moon = function/class — with nested orbits and click-to-descend navigation.
- **Procedural texture engine** (built in-house, zero image assets): planet terrain with continents/polar caps/craters, cratered moons with ray systems, plasma stars with sunspots and pulsing coronas, spiral-galaxy disc with dust lanes, turbulent nebulae, ringed planets.
- Camera rig with eased fly-to focus per hierarchy level; hover labels; HUD status bar showing backend/AI/index health.

### 4.4 Skills & Reports
- One-click execution against the active workspace; per-workspace disk caching; Markdown export per skill.
- Structured failure codes surfaced to the UI (`OLLAMA_UNAVAILABLE`, `MODEL_MISSING`, …) instead of silent errors.

### 4.5 Operations
- Multi-provider LLM management at runtime (`/api/settings`, persisted YAML, no restart).
- LLM telemetry: requests, failures, rate limits, latency, per-key health, fallback chain audit log.
- MCP tool layer (filesystem, GitHub, git, browser, terminal safe-mode) with hot-reloadable config.
- Supabase auth (email/password, admin-backed registration without confirmation emails) and cloud persistence for repositories/jobs/conversations.

---

## 5. Architecture Snapshot

```
React + Three.js frontend
        │ REST + WebSocket (JWT)
FastAPI backend
   ├─ Parser/Chunker → Embeddings → ChromaDB + BM25   (ingestion)
   ├─ LangGraph agent (10 nodes) + Hybrid RAG          (chat)
   ├─ Skills layer (9 analyses)                        (reports)
   ├─ LLM router: chat→Groq→Ollama·, analysis→Ollama→Groq· (+OpenAI/Gemini/OpenRouter/HF)
   ├─ MCP tool servers                                 (tools)
   └─ Supabase auth + persistence                      (cloud)
```
Full detail: [ARCHITECTURE.md](ARCHITECTURE.md) · [system_design.md](system_design.md).

---

## 6. Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, TypeScript, Vite, Three.js (+ react-three-fiber/drei), Tailwind, Framer Motion, react-router v6, Supabase JS |
| Backend | Python, FastAPI, Uvicorn, Pydantic v2, LangGraph, LangChain |
| AI/LLM | Groq (`openai/gpt-oss-20b`/`120b`), Ollama (`qwen3:8b`), OpenAI, Gemini 2.0 Flash, OpenRouter, HuggingFace Inference; embeddings `bge-small-en-v1.5` → Gemini → local SentenceTransformer |
| Storage | ChromaDB (persistent, cosine HNSW), custom in-memory BM25, YAML/JSON config, Supabase Postgres (cloud) |
| Infra | Docker, Procfile, render.yaml, Railway; git CLI for cloning |

---

## 7. Key Engineering Decisions

| Decision | Rationale |
|---|---|
| **Split task routing: chat → Groq, analysis → local qwen** | Chat needs snappy replies (Groq ≈ 1–2 s); skills/indexing tolerate slower local inference, keeping code on-device and costs near zero. Cloud providers are only fallbacks. |
| **Ollama as immediate fallback after Groq** | If the Groq key dies, chat lands on local qwen instead of cascading through other cloud providers — the failure mode degrades to "slower", never "down". |
| **Multiple API keys per provider (comma-separated, round-robin)** | Survives per-key rate limits; dead keys are health-marked and skipped automatically. |
| **Hybrid RAG with RRF instead of pure vector search** | Code identifiers are exact-match friendly (BM25) while semantics need embeddings; fusion consistently beats either alone. |
| **AST-aware chunking** | Chunks respect function/class boundaries → retrieved passages are complete, compilable units, not arbitrary 1000-char slices. |
| **Procedural textures over image assets** | Zero binary downloads, infinite variety per body (seeded), tiny repo, works offline. |
| **Fail-soft subsystem startup** | Parser/MCP/cloud-routes each init in try/except so a broken optional subsystem can't take the API down. |
| **Grounding guardrails** | Intent classifier + mandatory citations + verification node — the agent must say "Not Found" rather than invent. |
| **Local-first with explicit timeout** | Slow local inference ≠ failure: 600 s timeout prevents premature cloud failover (configurable `OLLAMA_TIMEOUT`). |

---

## 8. Development Journey & Challenges Solved

- **Port confusion (7860 vs 8000):** the frontend defaulted to one port while docs/deployment targeted another; resolved by standardizing on 7860 (HF Spaces convention), fixing `.env.local`, and removing stale UI text. Lesson: single source of truth for `VITE_API_URL`.
- **"Auth is not configured" on sign-in:** the frontend lacked Supabase env vars that only the backend had. Fixed by provisioning the **publishable** anon key to the frontend (service key stays backend-only) — and clarifying the split of secrets.
- **LLM latency complaints:** a local-only setup made every reply wait on CPU inference. Fixed with task-based routing (cloud for chat, local for batch analysis) and a documented timeout policy distinguishing "slow" from "down".
- **Dots-and-lines visuals:** early prototypes rendered wireframe icosahedrons and flat point clouds. Replaced with a real procedural texture engine (value noise, granulation, crater bump maps, spiral-arm discs) — no new dependencies, memoized generation.
- **Premature failover:** short timeouts caused local jobs to bounce to cloud mid-generation. Fixed with generous local timeouts + fallback-chain reordering (ollama promoted as immediate fallback after any cloud primary).
- **Fragile LLM resolution:** a `NameError` regression in model resolution was caught by router regression tests; tests now pin routing for every task.

---

## 9. Results

| Metric | Value |
|---|---|
| Backend endpoints | 25+ REST routes, 1 streaming WebSocket |
| Agent graph | 10 nodes, 2 self-correction loops, parallel tool execution |
| Skills | 9 (3 static, 6 LLM-powered) with Markdown export |
| LLM providers | 6 with key rotation + ordered failover; telemetry audit log |
| Supported languages (parsing) | Python, JS/TS AST; 14+ extensions indexed |
| Frontend | 3D universe @ 60fps target; textures 100% procedural; bundle ≈ 1.4 MB (min) |
| Tests | Backend regression suites for routers, skills, LLM status, API |

---

## 10. Limitations & Future Work

**Known limitations**
- CPU-only local inference is slow for large repos (mitigated by cloud chat routing and OLLAMA_TIMEOUT tuning).
- Single active workspace per backend instance.
- Production bundle is large (Three.js); no code-splitting yet.
- AST chunking currently deep for Python/JS-TS; other languages use generic splitting.

**Roadmap**
1. Code-split the frontend (Three.js lazy chunk) and add bloom post-processing toggle.
2. Embeddings worker with incremental re-index on file change (file watcher).
3. Team features: shared universes, comment threads pinned to code bodies in 3D.
4. More language analyzers (Go, Rust, Java) via tree-sitter.
5. Evaluation harness for retrieval quality (golden question/answer sets, recall@k dashboards).
6. GitHub App mode: index on push, PR review skills.

---

## 11. Conclusion

RepoVerse AI demonstrates a complete, production-shaped AI engineering workflow: **ingest → chunk → embed → retrieve → orchestrate → verify → visualize**. Its differentiators are the grounding guardrails (citations + "Not Found" honesty), the pragmatic local-first/cloud-fallback LLM economics, resilient multi-provider failover with key rotation, and a genuinely fun 3D interface that makes codebase structure *spatially* intuitive. The codebase itself is organized exactly as its own architecture prescribes — modular layers, typed contracts, telemetry, and fail-soft startup — making it ready for both hackathon showcase and real-world team adoption.
