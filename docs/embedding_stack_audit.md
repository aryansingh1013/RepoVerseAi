# RepoVerse AI — Embedding & Indexing Stack Audit

**Date:** 2026-09-09 · **Scope:** `backend/rag/vector_store.py`, `backend/rag/retriever.py`,
`backend/rag/bm25_index.py`, `/api/index` flow in `backend/app.py`, ChromaDB usage, and the
deployment realities (Render free tier / Railway hobby). **Method:** static reading + live
reproduction in a clean Python env + current vendor-status checks.

---

## Executive summary

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | Step 1 of the embedding cascade calls the **legacy HF Inference API, which is permanently decommissioned** (410 Gone) | 🔴 Critical | Dead code path, always fails |
| 2 | Step 2 calls **Gemini `text-embedding-004`, retired Jan 14 2026**, via the deprecated `google-generativeai` SDK | 🔴 Critical | Dead even with a valid key |
| 3 | ⇒ The only *live* provider is local `sentence-transformers` (torch), which **crashes if absent** and **cannot fit in 512 MB** (Render free / Railway hobby) | 🔴 Critical | Hosted indexing is effectively broken |
| 4 | ChromaDB lives in `settings.DB_DIR` on Render's **ephemeral filesystem** (disks = paid plans only) — the index dies on every redeploy | 🟠 High | Persistence is an illusion on server |
| 5 | **Stale-index bug:** `/api/index` cache short-circuit skips re-chunking forever, as long as *any* cached file still exists — new/changed files never enter the index | 🟠 High | Silent data drift |
| 6 | **No dimension coherence guard:** 384 (bge-small) vs 768 (Gemini) vs 3072 (gemini-embedding-001) can mix in one collection; `embed_query` falls back to a hardcoded `[0.0] * 384` | 🟠 High | Corrupt/garbage retrieval when any API path is revived |
| 7 | Retriever filename filter is an **exact match** (`where={"path": "app.py"}` vs stored `"backend/app.py"`) → scoped queries silently return **zero** chunks | 🟡 Medium | Answer-quality regression |
| 8 | Free-tier spin-down kills long-lived sockets; `/ws/chat` has no reconnect (one WS per message mitigates it) | 🟢 Low | UX friction only |

**Bottom line:** the vector store choice (Chroma) is *not* the broken part of this stack — the
**embedding providers feeding it are**. Today, on a hosted deployment, indexing either crashes
(no torch), OOMs (torch on 512 MB), or writes into a directory that vanishes at the next
redeploy. Fixing the provider is mandatory regardless of which store you keep.

---

## Evidence & detail

### Finding 1 — legacy HF endpoint is gone
`EmbeddingsManager._embed_via_hf_api` POSTs to
`https://api-inference.huggingface.co/pipeline/feature-extraction/{model}`.
HF decommissioned `api-inference.huggingface.co` by late 2025; it now returns **410 Gone**
("no longer supported, use router.huggingface.co") — confirmed in multiple vendor migration
reports and third-party bug trackers. The failure is swallowed by a bare `except → return None`,
so the only trace is a print line; every `embed_texts` call pays a wasted round-trip first.

### Finding 2 — Gemini embeddings are gone too
`_embed_via_gemini` uses `google.generativeai.embed_content(model="models/text-embedding-004")`.
`text-embedding-004` was deprecated on **2026-01-14**; the API now errors with
`models/text-embedding-004 is not found ... or is not supported for embedContent`. Replacement:
`gemini-embedding-001` (native 3072 dims, MRL-truncatable to 768/512/256/128), called via the
new **`google-genai`** SDK (`google-generativeai` itself is end-of-life).

### Finding 3 — the silent consequence: local torch is the only path (live-repro'd)
Reproduced in a clean venv without optional packages:

```text
EmbeddingsManager: HF Inference API failed: ... api-inference.huggingface.co ... (DNS error)
EmbeddingsManager: Falling back to local SentenceTransformer...
EmbeddingsManager: Local model load failed: No module named 'sentence_transformers'
CASCADE RESULT: embed_texts CRASHED -> ModuleNotFoundError
```

Notes:
- A `ModuleNotFoundError` inside `sync_index` surfaces as **HTTP 500 from `/api/index`** — the
  hosted indexer dies unless torch is installed.
- If torch *is* installed (it's in `requirements.txt`): runtime RAM for FastAPI + torch + bge-small
  typically sits around/above **512 MB**, i.e. Render free tier and Railway hobby territory.
  Cold model load also adds ~10–30 s to the first index after every boot (which happens a lot on
  free tiers that spin down).
- The Docker image carries ~2–3 GB of torch for one inference call pattern — build times on
  Render free suffer accordingly.

### Finding 4 — Chroma's persistence doesn't survive the platform
`VectorStore` = `chromadb.PersistentClient(path=settings.DB_DIR)` with `DB_DIR = <repo>/db`.
Render: filesystem is **ephemeral; persistent disks require a paid plan** (docs: render.com/docs/disks).
Same story on Railway hobby without a volume. Consequences:
- The `use_cache` fast path in `/api/index` can *never* hit after a redeploy — the cache exists
  only for the lifetime of one container.
- The last upstream commit ("persist active workspace path across reloads and server restarts",
  `active_workspace.json`) is a symptom of the same platform constraint: **anything written to
  disk is app state that shouldn't be on disk in this deployment model.**
- Cloned repos (`db/cloned_repos`) are re-cloned on every deploy as well.

### Finding 5 — the cache short-circuit makes the index go stale
`backend/app.py::index_galaxy` (cache branch): if `collection.count() > 0` **and the first cached
chunk's path still exists**, the freshly built `all_chunks` is *discarded* and the index is
served from Chroma. Effects: files added/edited after the first index are **never embedded**
until someone clears `db/` manually; the "Successfully indexed N chunks" message then reports
cache size, not reality. There is no per-file hash/mtime invalidation.

### Finding 6 — dimension coherence is undefended
Three providers, three dims: `BAAI/bge-small-en-v1.5` → 384, `text-embedding-004` → 768,
`gemini-embedding-001` → 3072 (768 if truncated). Chroma won't stop a mixed collection, and
`embed_query()`'s "provider offline" fallback returns a hardcoded zero vector of **384** — a
silent wrong-answer generator (cosine of a zero vector is meaningless). There is no config-level
"one model, one dim, one collection" contract.

### Finding 7 — filename-scoped queries self-destruct
`nodes.retriever_node` regexes `in <name>` out of the query and issues `where={"path": name}`.
Stored metadata holds the **relative** path (`backend/app.py`); an exact filter on `app.py` matches
nothing — for both the vector leg and the manual BM25 post-filter. The user gets "couldn't
retrieve any relevant codebase context" precisely when they were most specific.

### Finding 8 — transport notes (low)
Free instances spin down after ~15 min idle → first request pays a cold start; any open
WebSocket dies. The frontend opens a fresh WS per message and shows an error bubble, so this is
UX friction rather than corruption.

---

## What's actually fine

- The **hybrid retrieval design** (vector + BM25 + RRF, k=60) is correct and cheap — hand-rolled
  BM25 in `bm25_index.py` works. Caveat: it's in-memory only and re-fit at each `/api/index`
  call **from the same (possibly stale) chunk list** — so on desktop, where the Chroma cache *is*
  durable, Finding 5 drifts both legs of retrieval; on the server it "resets" only because
  Finding 4 wipes everything between deploys.
- **Chroma usage itself is clean** — batched upserts (32), explicit embeddings (no hidden default
  embedding function), JSON-serialized list metadata with matching deserialization, `clear()` by
  ids. Collection-per-workspace hashing is a reasonable isolation pattern *for a single user*.
- AST-first chunking (`chunk_builder`) produces the line-range metadata that grounds citations —
  the whole "Moons" pipeline is sound; it's the storage/provider layer that hurts.

---

## Fix options for the embedding provider (pick one — mandatory for any of the store plans)

| Option | Dims | Cost | Notes |
|---|---|---|---|
| **A. HF Inference Providers** via `router.huggingface.co` (OpenAI-style client), same `bge-small` model | 384 | Free tier w/ HF_TOKEN, then metered | Smallest change; keeps dims = collection format = zero-vector fallback consistent; rate limits apply |
| **B. OpenAI `text-embedding-3-small`** | 1536 | ~$0.02 / M tokens (re-indexing this whole repo ≈ < $0.01) | Robust, boring, fast; requires dropping zero-vector fallback + storing dim in config |
| **C. `google-genai` + `gemini-embedding-001` @ `output_dimensionality=768`** | 768 (truncated) | Free tier | Fixes both the model *and* the dead SDK; new `embed_content` lives on the `google-genai` client |
| **D. Local torch, but a real host** (≥1 GB RAM, paid tier or VPS) | 384 | $0 / mo | Works, but keeps the cold-start + image-size pain; pair with a persistent disk |

## Store decision given the audit

- **P1 hybrid (Supabase data layer, keep Chroma)** is now *only* defensible if you accept
  "hosted index = per-boot cache, rebuilt via Option A/B/C" and single-user hosting.
- **P1 + pgvector (Supabase as the one store)** gains new arguments: it permanently kills
  Findings 4, 5, 6 (mtime/hash column per file → incremental re-embeds in SQL; RLS isolation;
  `chunks` joins with telemetry for the analytics you asked for). The `VectorStore` surface to
  reimplement is ~150 lines (`add_chunks`, `search`, `clear`, plus two raw `collection.*` calls
  in `app.py`).
- Whichever wins: also delete the zero-vector fallback (raise instead), guard provider dims at
  write time, and fix the `where` filter with a suffix match (`$in` over matching paths or drop
  the filter and re-rank).

---

*Prepared during the P0-hardening session branch; companion to the Security Model section in README.md.*
