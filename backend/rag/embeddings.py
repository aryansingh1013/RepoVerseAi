"""Embedding providers for RepoVerse AI — post-audit rewrite (2026-09-09).

Replaces the old EmbeddingsManager cascade which silently targeted two dead
endpoints (legacy api-inference.huggingface.co — 410 Gone since late 2025 —
and Gemini text-embedding-004 — retired 2026-01-14).

Contract enforced here (audit findings #1, #2, #6):
* ONE (provider, model, dimensions) tuple is *pinned* for the process lifetime
  and shared by documents and queries, so a collection can never mix
  dimensionalities. `fingerprint` keys the vector collection/table.
* No zero-vector fallback. If no provider can serve, raise ``EmbeddingError``
  with the exact env vars to configure.
* Providers that cannot produce the configured ``EMBEDDING_DIMENSIONS`` are
  skipped (or error, when one provider was explicitly forced).

Candidate order (auto): OpenAI text-embedding-3-small → Hugging Face router
(``router.huggingface.co/v1`` OpenAI-compatible /embeddings, keeps the repo's
BAAI/bge-small-en-v1.5 @ 384-dim default) → Google ``google-genai``
gemini-embedding-001 (MRL-truncatable) → local sentence-transformers.
"""

from typing import Dict, Any, List, Optional

from backend.core.config import settings

OPENAI_MODEL = "text-embedding-3-small"
OPENAI_NATIVE_DIMS = 1536
OPENAI_ALLOWED_DIMS = {256, 512, 1024, 1536}

GEMINI_MODEL = "models/gemini-embedding-001"
GEMINI_NATIVE_DIMS = 3072
GEMINI_ALLOWED_DIMS = {3072, 1536, 768, 512, 256, 128}

HF_NATIVE_DIMS = 384  # for BAAI/bge-small-en-v1.5

# bge-v1.5 recommends an instruction prefix on retrieval queries.
BGE_QUERY_PREFIX = "Represent the user's query for codebase retrieval: "


class EmbeddingError(RuntimeError):
    pass


class Embeddings:
    def __init__(self):
        self._pinned: Optional[Dict[str, Any]] = None
        self._local_model = None

    # ── candidate resolution ─────────────────────────────────────────────────

    def _configured(self) -> List[Dict[str, Any]]:
        target = settings.EMBEDDING_DIMENSIONS
        explicit = (settings.EMBEDDING_PROVIDER or "auto").strip().lower()
        cands: List[Dict[str, Any]] = []

        def wants(name: str) -> bool:
            return explicit in ("auto", "", name)

        if wants("openai") and settings.OPENAI_API_KEY:
            dims = OPENAI_NATIVE_DIMS if target is None else (
                target if target in OPENAI_ALLOWED_DIMS else None
            )
            if dims:
                cands.append({"provider": "openai", "model": OPENAI_MODEL, "dimensions": dims})
            elif explicit == "openai":
                raise EmbeddingError(
                    f"OpenAI embeddings cannot produce EMBEDDING_DIMENSIONS={target}; "
                    f"use one of {sorted(OPENAI_ALLOWED_DIMS)}."
                )

        if wants("huggingface") and settings.HF_TOKEN:
            dims = HF_NATIVE_DIMS if target in (None, HF_NATIVE_DIMS) else None
            if dims:
                cands.append({
                    "provider": "huggingface",
                    "model": settings.EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5",
                    "dimensions": dims,
                })
            elif explicit == "huggingface":
                raise EmbeddingError(
                    f"HF router model '{settings.EMBEDDING_MODEL}' is {HF_NATIVE_DIMS}-dim but "
                    f"EMBEDDING_DIMENSIONS={target}. Pick a matching model or unset dimensions."
                )

        if wants("gemini") and settings.GEMINI_API_KEY:
            dims = GEMINI_NATIVE_DIMS if target is None else (
                target if target in GEMINI_ALLOWED_DIMS else None
            )
            if dims:
                cands.append({"provider": "gemini", "model": GEMINI_MODEL, "dimensions": dims})
            elif explicit == "gemini":
                raise EmbeddingError(
                    f"gemini-embedding-001 cannot produce EMBEDDING_DIMENSIONS={target}; "
                    f"supported truncations: {sorted(GEMINI_ALLOWED_DIMS)}."
                )

        if wants("local"):
            try:
                import sentence_transformers  # noqa: F401
            except ImportError:
                sentence_transformers = None
            if sentence_transformers is not None:
                # Dimensions are learned from the model on first pin below; for
                # bge-small / MiniLM defaults this is 384 — verify against target.
                probe_dims = target if target is not None else HF_NATIVE_DIMS
                cands.append({
                    "provider": "local",
                    "model": settings.EMBEDDING_MODEL or "BAAI/bge-small-en-v1.5",
                    "dimensions": probe_dims,
                    "probed": target is None,  # must verify after model load
                })

        if explicit not in ("auto", "") and not cands:
            raise EmbeddingError(
                f"EMBEDDING_PROVIDER='{explicit}' requested but its API key is not configured. "
                f"Set the matching *_API_KEY/HF_TOKEN in backend/.env."
            )
        return cands

    @property
    def candidates(self) -> List[Dict[str, Any]]:
        return self._configured()

    def ensure_pinned(self) -> Dict[str, Any]:
        """Deterministically fix (provider, model, dimensions) for this process.

        No network call: pinning from config keeps collection naming stable
        across restarts. Actual calls may fall back to other candidates that
        honor the SAME pinned dimensions (never different dims)."""
        if self._pinned is not None:
            return self._pinned
        cands = self.candidates
        if not cands:
            raise EmbeddingError(
                "No usable embedding provider. Configure one of: OPENAI_API_KEY (recommended, "
                "text-embedding-3-small), HF_TOKEN (free tier via router.huggingface.co with "
                "BAAI/bge-small-en-v1.5 @384), GEMINI_API_KEY (google-genai), or install "
                "sentence-transformers for local mode. (Zero-vector fallback was removed: a "
                "silent 0.0 embed returns silently wrong retrieval.)"
            )
        self._pinned = dict(cands[0])
        return self._pinned

    @property
    def fingerprint(self) -> str:
        p = self.ensure_pinned()
        return f"{p['provider']}:{p['model']}:{p['dimensions']}"

    @property
    def dimensions(self) -> int:
        return int(self.ensure_pinned()["dimensions"])

    # ── provider calls ────────────────────────────────────────────────────────

    def _embed_openai(self, texts: List[str], cand: Dict[str, Any]) -> List[List[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        out: List[List[float]] = []
        for i in range(0, len(texts), 64):
            batch = texts[i:i + 64]
            kwargs = {"model": cand["model"], "input": batch}
            if cand["dimensions"] != OPENAI_NATIVE_DIMS:
                kwargs["dimensions"] = cand["dimensions"]
            resp = client.embeddings.create(**kwargs)
            out.extend([d.embedding for d in resp.data])
        return out

    def _embed_huggingface(self, texts: List[str], cand: Dict[str, Any], is_query: bool = False) -> List[List[float]]:
        from openai import OpenAI
        client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=settings.HF_TOKEN)
        if is_query and "bge" in cand["model"].lower():
            texts = [BGE_QUERY_PREFIX + t for t in texts]
        out: List[List[float]] = []
        for i in range(0, len(texts), 32):
            resp = client.embeddings.create(model=cand["model"], input=texts[i:i + 32])
            out.extend([d.embedding for d in resp.data])
        return out

    def _embed_gemini(self, texts: List[str], cand: Dict[str, Any], is_query: bool = False) -> List[List[float]]:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        out: List[List[float]] = []
        for i in range(0, len(texts), 32):
            batch = texts[i:i + 32]
            config = types.EmbedContentConfig(
                output_dimensionality=cand["dimensions"],
                task_type="RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT",
            )
            resp = client.models.embed_content(model=cand["model"], contents=batch, config=config)
            out.extend([list(e.values) for e in resp.embeddings])
        return out

    def _embed_local(self, texts: List[str], cand: Dict[str, Any], is_query: bool = False) -> List[List[float]]:
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(cand["model"])
            import numpy as np  # noqa: F401  (sanity import to fail fast)
            probe = self._local_model.encode(["dimension probe"], show_progress_bar=False)
            native = int(probe.shape[1])
            if cand.get("probed"):
                cand["dimensions"] = native
                if self._pinned is not None and self._pinned.get("provider") == "local":
                    self._pinned["dimensions"] = native
            if native != int(cand["dimensions"]):
                raise EmbeddingError(
                    f"Local model '{cand['model']}' yields {native}-dim vectors but the pinned "
                    f"schema expects {cand['dimensions']}. Align EMBEDDING_MODEL/EMBEDDING_DIMENSIONS."
                )
        if is_query and "bge" in cand["model"].lower():
            texts = [BGE_QUERY_PREFIX + t for t in texts]
        vecs = self._local_model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]

    # ── public API ────────────────────────────────────────────────────────────

    def _run(self, texts: List[str], is_query: bool) -> List[List[float]]:
        if not texts:
            return []
        pinned = self.ensure_pinned()
        # Candidate list, pinned first, same-dims only for silent fallback.
        order = [pinned] + [
            c for c in self.candidates
            if c["provider"] != pinned["provider"] and c["dimensions"] == pinned["dimensions"]
        ]
        errors: List[str] = []
        for cand in order:
            try:
                if cand["provider"] == "openai":
                    vecs = self._embed_openai(texts, cand)
                elif cand["provider"] == "huggingface":
                    vecs = self._embed_huggingface(texts, cand, is_query=is_query)
                elif cand["provider"] == "gemini":
                    vecs = self._embed_gemini(texts, cand, is_query=is_query)
                elif cand["provider"] == "local":
                    vecs = self._embed_local(texts, cand, is_query=is_query)
                else:
                    continue
                # Final guard — the contract is enforced at the wire boundary.
                dim = int(pinned["dimensions"])
                for v in vecs:
                    if len(v) != dim:
                        raise EmbeddingError(
                            f"Provider '{cand['provider']}' returned {len(v)}-dim vector; "
                            f"pinned schema is {dim}-dim. Refusing to mix dimensionalities."
                        )
                self.last_provider = f"{cand['provider']} / {cand['model']}"
                return vecs
            except EmbeddingError:
                raise
            except Exception as exc:
                errors.append(f"{cand['provider']}: {type(exc).__name__}: {str(exc)[:200]}")
        raise EmbeddingError(
            "All embedding providers failed — indexing aborted (no zero-vector fallback). "
            + " | ".join(errors)
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._run(texts, is_query=False)

    # Back-compat alias for the old EmbeddingsManager API.
    embed_texts = embed_documents

    def embed_query(self, text: str) -> List[float]:
        res = self._run([text], is_query=True)
        return res[0]


# Legacy import path (e.g. older scripts) keeps working.
EmbeddingsManager = Embeddings
