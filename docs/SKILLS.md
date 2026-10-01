# RepoVerse AI — Skills Reference

All 9 skills run against the **currently selected universe** (the active workspace).
They are invoked from the frontend **Skills Intelligence Console** (`SkillsOverlay`)
and executed on the backend through the central LLM router — no skill talks to
Ollama or any cloud provider directly.

---

## 1. Skill Inventory

| # | Slug | Name | What it does | Deterministic core | LLM usage | RAG |
|---|------|------|--------------|--------------------|-----------|-----|
| 1 | `overview` | Repository Overview | Tech stack, language metrics, entry points, top-level folder layout | 100% static scan | None | No |
| 2 | `architecture` | Architecture Analyzer | Layer descriptions + Mermaid structural diagram | Workspace skeleton | 1 call, JSON | No |
| 3 | `health` | Health Analyzer | Code-quality issues (long functions, bare excepts, TODOs) + 0–100 score | AST analysis | Recommendations only (degrades visibly) | No |
| 4 | `dependencies` | Dependency Explorer | Import graph, external packages, **circular dependency chains** | AST + regex + DFS cycle detection | None | No |
| 5 | `timeline` | Git Timeline | Commit history, contributors, real total commit count | `git log` / `rev-list` | None | No |
| 6 | `learning` | Learning Mode | Onboarding lessons + multiple-choice quiz | Workspace skeleton | 1 call, JSON | No |
| 7 | `readme` | README Generator | Full README.md grounded in the actual repo structure | Scan + existing README | 1 call, markdown | No |
| 8 | `security` | Security Review | Regex scan for secrets/dangerous patterns + posture summary | Static regex scan | Summary only (degrades visibly) | No |
| 9 | `performance` | Performance Review | Large files, deep nesting, sync-blocking calls + improvement insights | AST heuristics | Insights only (degrades visibly) | No |

**RAG note:** skills consume repository data via the shared filesystem walker
(`backend/skills/utils.py: safe_walk`), not the ChromaDB/BM25 pipeline. Chat
(`/ws/chat`) is the RAG consumer. Skills never touch other universes' data —
see §3.

---

## 2. Universe Context (source of truth)

Every skill resolves the same chain:

```text
backend/core/active_workspace.json  →  settings.WORKSPACE_DIR
                                    →  validate_workspace()   (hard gate)
                                    →  skill.execute(query, agent_graph, workspace_dir)
```

- If no universe is selected or the path no longer exists, the API returns a
  structured error — it never falls back to another directory:

```json
{
  "success": false,
  "skill": "architecture",
  "error": { "code": "NO_UNIVERSE_SELECTED", "message": "No repository/universe is currently selected." }
}
```

- Switching universes: `POST /api/workspace/select` (local path) or
  `POST /api/clone` (GitHub URL). The active path is persisted and reused on
  backend restart.

---

## 3. Universe Isolation Rules

`safe_walk` (single shared walker for all skills) enforces:

- `SKIP_DIRS` excludes `db/` and `db/cloned_repos/` — those directories hold
  **other universes'** cloned repositories and vector index files. Scanning
  them would mix foreign repository content into reports.
- Hidden directories, `node_modules`, build output, and files > 1.5 MB are
  excluded.
- Unreadable files/directories are surfaced as warnings in backend logs, not
  silently swallowed.

Caching is per-workspace: results are stored in `<workspace>/.repoverse/skills_cache.json`,
so two universes never share cache entries.

---

## 4. LLM Integration (local-first)

```text
Skill → analyze_with_llm() → model_router.generate(task="analysis")
      → task_router → (ollama, qwen3:8b)
      → provider_router → OllamaProvider (OpenAI-compatible, localhost:11434/v1)
```

- **Default provider/model:** Ollama / `qwen3:8b`. Cloud providers are
  fallback-only and are skipped automatically when no API key is configured.
- **Timeout:** `OLLAMA_TIMEOUT` (default **600 s**). Local CPU inference of
  structured JSON with qwen3:8b can take several minutes; a short timeout
  would silently fail over to the cloud, which violates local-first policy.
- **Thinking blocks:** qwen3-style `<think>…</think>` output is stripped before
  parsing.
- **Structured output:** JSON is extracted and validated per skill. On failure
  the skill raises `SkillLLMError` with one of these codes:

| Code | Meaning | Fix |
|------|---------|-----|
| `OLLAMA_UNAVAILABLE` | Ollama not reachable | `ollama serve` |
| `MODEL_MISSING` | Model not pulled | `ollama pull qwen3:8b` |
| `JSON_PARSE_FAILED` | Model returned malformed JSON | Re-run the skill |
| `EMPTY_LLM_RESULT` | Model returned nothing usable | Re-run the skill |
| `LLM_GENERATION_FAILED` | All providers in the chain failed | Check `ollama list`, provider keys |

- **Failures are never cached.** A cached result exists only if the skill
  genuinely completed. Use `POST /api/skills/clear-cache/{slug}` (or `all`)
  to force a re-run.
- Hybrid skills (`security`, `performance`, `health`) return their deterministic
  results even when the LLM is down, with a visible `warnings` array — they do
  not fabricate LLM content.

### Health & status

- `GET /api/llm/status` — real Ollama connectivity + model availability +
  workspace + index chunk count. The frontend status bar renders this;
  nothing is hard-coded client-side.

---

## 5. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/skills` | List registered skills |
| POST | `/api/skills/execute/{slug}` | Execute a skill for the active universe |
| POST | `/api/skills/export/{slug}` | Render a skill result as a Markdown report |
| POST | `/api/skills/clear-cache/{slug}` | Clear cache for one skill or `all` |
| GET | `/api/llm/status` | LLM + workspace + index capability status |

---

## 6. Environment Variables (backend/.env)

```env
# Local-first LLM (recommended defaults)
OLLAMA_ENDPOINT=http://localhost:11434/v1
OLLAMA_DEFAULT_MODEL=qwen3:8b
OLLAMA_TIMEOUT=600

# Optional cloud fallbacks (leave empty to stay fully local)
GROQ_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
HF_TOKEN=

# Embeddings (chat RAG pipeline)
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

Secrets are backend-only; the frontend never receives API keys or tokens.

---

## 7. Running RepoVerse Locally

```bash
# 1. Local LLM
ollama serve          # if not already running
ollama pull qwen3:8b
ollama list           # confirm qwen3:8b is present

# 2. Backend (from project root)
pip install -r requirements.txt
python app.py         # serves on PORT (default 8000; app.py defaults 7860)

# 3. Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Then: open the app → clone/select a repository → wait for indexing →
open **Skills** and run any skill.

---

## 8. Testing

```bash
# Unit + integration suite (universe isolation, skill logic, LLM failure handling)
python -m pytest backend/test_skills.py -v

# Quick capability probe
curl http://localhost:8000/api/llm/status

# Execute a skill against the active universe
curl -X POST http://localhost:8000/api/skills/execute/architecture
```

The pytest suite includes the **universe isolation test** (§18): two temporary
universes are created, unique markers are planted in each, and every scan-based
skill is asserted to never leak the other universe's content.

---

## 9. Known Limitations

- **Local generation is slow on CPU.** First run of an LLM skill can take
  3–10+ minutes with qwen3:8b on CPU (results are cached afterwards). Lower
  `OLLAMA_TIMEOUT` only if you run on GPU.
- **Embeddings are cloud-first** in the chat RAG pipeline (HF → Gemini →
  local SentenceTransformer fallback). If `HF_TOKEN` is set, chat indexing
  sends chunk text to the HF Inference API. Skills themselves never make
  network calls.
- **Dependency Explorer** reports the first 80 import relations (of the full
  set; `total_relations` reports the true count) and caps cycle output at 10.
- **Security/health scans** are heuristic (regex/AST), not a substitute for a
  real SAST tool.
- **Timeline** needs `git` on PATH and a `.git` directory in the workspace;
  otherwise it degrades to a clear "no git history" result.
- TypeScript/JS dependency resolution uses regex imports and index-file
  heuristics, not a full bundler graph.
