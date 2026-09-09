"""Supabase / Postgres + pgvector backend (P1+P1.5).

Same public surface as the Chroma ``VectorStore`` so the factory can swap them:
count, search, upsert_file, delete_file, load_all_chunks, file_manifest,
paths_matching, clear.

Requires the schema in backend/sql/schema.sql applied to the Supabase project
(the ``chunks.embedding`` column is vector(384) to match the default
EMBEDDING_DIMENSIONS — the file documents the ALTER for other dims).

Persistence model that fixes audit findings #4/#5:
* chunk rows + per-file ``content_hash`` live in Postgres, so the index
  survives redeploys and scales to multi-user via RLS later;
* re-indexing is incremental: the caller (index_service) only sends files
  whose hash changed.
"""

import os
import hashlib
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.rag.embeddings import Embeddings, EmbeddingError


class SupabaseVectorStore:
    def __init__(self, client: Any = None):
        self.embeddings = Embeddings()
        self._client = client
        self._ready_workspaces: set = set()

    # ── plumbing ──────────────────────────────────────────────────────────────

    @property
    def client(self):
        if self._client is None:
            url = (settings.SUPABASE_URL or "").strip()
            key = (settings.SUPABASE_SERVICE_ROLE_KEY or "").strip()
            if not url or not key:
                raise RuntimeError(
                    "VECTOR_BACKEND=supabase requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                    "in backend/.env, and backend/sql/schema.sql applied to the project."
                )
            try:
                from supabase import create_client
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("pip install supabase to use VECTOR_BACKEND=supabase") from exc
            self._client = create_client(url, key)
        return self._client

    @property
    def workspace_key(self) -> str:
        return hashlib.md5(os.path.abspath(settings.WORKSPACE_DIR).encode("utf-8")).hexdigest()[:16]

    def _ensure_workspace(self):
        key = self.workspace_key
        if key in self._ready_workspaces:
            return
        fp = self.embeddings.fingerprint
        root = os.path.abspath(settings.WORKSPACE_DIR)
        try:
            res = (
                self.client.table("workspaces")
                .select("key,embed_fingerprint")
                .eq("key", key)
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            if rows and rows[0].get("embed_fingerprint") != fp:
                print(
                    f"SupabaseStore: embedding fingerprint changed "
                    f"({rows[0].get('embed_fingerprint')!r} -> {fp!r}); clearing stale chunks for rebuild."
                )
                self.clear(keep_manifest=False)
            self.client.table("workspaces").upsert(
                {"key": key, "root_path": root, "embed_fingerprint": fp}
            ).execute()
        except Exception as exc:
            raise RuntimeError(f"SupabaseStore: workspace bootstrap failed: {exc}") from exc
        self._ready_workspaces.add(key)

    # ── file manifest (incremental index state) ──────────────────────────────

    def file_manifest(self) -> Dict[str, str]:
        self._ensure_workspace()
        res = (
            self.client.table("files")
            .select("path,content_hash")
            .eq("workspace_key", self.workspace_key)
            .execute()
        )
        return {r["path"]: r["content_hash"] for r in (getattr(res, "data", None) or [])}

    def paths_matching(self, suffix: str) -> List[str]:
        suffix = (suffix or "").strip().lower().lstrip("./\\")
        if not suffix:
            return []
        return sorted(
            p for p in self.file_manifest()
            if p.lower().endswith(suffix) or p.lower() == suffix
        )

    # ── writes ────────────────────────────────────────────────────────────────

    def upsert_file(self, rel_path: str, chunks: List[Dict[str, Any]], content_hash: str,
                    mtime: float = 0.0, size: int = 0):
        """Replace all chunks for one file, then record its hash. Embedding is
        computed here so both store backends behave identically."""
        self._ensure_workspace()
        ws = self.workspace_key
        self.client.table("chunks").delete().eq("workspace_key", ws).eq("path", rel_path).execute()

        rows = []
        for idx, ch in enumerate(chunks):
            meta = ch.get("metadata", {})
            rows.append({
                "id": f"{ws}:{rel_path}:{idx}",
                "workspace_key": ws,
                "path": rel_path,
                "chunk_type": meta.get("chunk_type", ""),
                "language": meta.get("language", ""),
                "symbol_class": meta.get("class") or None,
                "symbol_function": meta.get("function") or None,
                "start_line": int(meta.get("start_line", 1) or 1),
                "end_line": int(meta.get("end_line", 0) or 0),
                "content": ch["content"],
                "extra_metadata": {
                    "imports": meta.get("imports", []),
                    "exports": meta.get("exports", []),
                    "summary": meta.get("summary", ""),
                },
            })
        if rows:
            vectors = self.embeddings.embed_documents([r["content"] for r in rows])
            for r, vec in zip(rows, vectors):
                r["embedding"] = vec
            for i in range(0, len(rows), 50):
                self.client.table("chunks").upsert(rows[i:i + 50]).execute()

        self.client.table("files").upsert({
            "workspace_key": ws,
            "path": rel_path,
            "content_hash": content_hash,
            "size_bytes": size,
            "mtime": mtime,
        }).execute()

    def delete_file(self, rel_path: str):
        self._ensure_workspace()
        ws = self.workspace_key
        self.client.table("chunks").delete().eq("workspace_key", ws).eq("path", rel_path).execute()
        self.client.table("files").delete().eq("workspace_key", ws).eq("path", rel_path).execute()

    def clear(self, keep_manifest: bool = False):
        ws = self.workspace_key
        self.client.table("chunks").delete().eq("workspace_key", ws).execute()
        if not keep_manifest:
            self.client.table("files").delete().eq("workspace_key", ws).execute()

    # ── reads ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        self._ensure_workspace()
        res = (
            self.client.table("chunks")
            .select("id", count="exact")
            .eq("workspace_key", self.workspace_key)
            .limit(1)
            .execute()
        )
        return int(getattr(res, "count", None) or 0)

    def load_all_chunks(self) -> List[Dict[str, Any]]:
        """Full corpus for BM25 fitting. Fine at repo scale (thousands of rows)."""
        self._ensure_workspace()
        res = (
            self.client.table("chunks")
            .select("*")
            .eq("workspace_key", self.workspace_key)
            .execute()
        )
        out = []
        for r in getattr(res, "data", None) or []:
            extra = r.get("extra_metadata") or {}
            out.append({
                "id": r["id"],
                "content": r["content"],
                "metadata": {
                    "path": r["path"],
                    "language": r.get("language", ""),
                    "class": r.get("symbol_class") or "",
                    "function": r.get("symbol_function") or "",
                    "chunk_type": r.get("chunk_type") or "",
                    "start_line": r.get("start_line", 1),
                    "end_line": r.get("end_line", 1),
                    "imports": extra.get("imports", []),
                    "exports": extra.get("exports", []),
                    "summary": extra.get("summary", ""),
                },
            })
        return out

    def search(self, query: str, limit: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._ensure_workspace()
        try:
            query_vec = self.embeddings.embed_query(query)
        except EmbeddingError:
            raise
        path_list: Optional[List[str]] = None
        if where:
            if "paths" in where:
                path_list = where.get("paths") or []
                if not path_list:
                    return []
            elif "path" in where:
                path_list = [where["path"]]
        res = self.client.rpc(
            "match_chunks",
            {
                "query_embedding": query_vec,
                "ws_key": self.workspace_key,
                "match_count": int(limit),
                "path_list": path_list,
            },
        ).execute()
        out = []
        for r in getattr(res, "data", None) or []:
            out.append({
                "id": r.get("id"),
                "content": r.get("content", ""),
                "metadata": r.get("metadata") or {"path": r.get("path", "")},
                "score": float(r.get("score", 0.0) or 0.0),
            })
        return out

    # Legacy API parity (some scripts call add_chunks directly)
    def add_chunks(self, chunks: List[Dict[str, Any]]):
        self._ensure_workspace()
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for ch in chunks:
            rel = ch.get("metadata", {}).get("path", "unknown")
            by_file.setdefault(rel, []).append(ch)
        for rel, group in by_file.items():
            self.upsert_file(rel, group, content_hash="", mtime=0.0, size=0)
