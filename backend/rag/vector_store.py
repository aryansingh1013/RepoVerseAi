"""Local ChromaDB-backed vector store (default backend).

Post-audit rewrite: the old file hard-coded a dead HF endpoint, an unusable
zero-vector fallback, and a global collection that could mix dimensionalities
across providers. Embedding is now delegated to backend.rag.embeddings
(single pinned provider/model/dim contract), the collection is keyed by that
fingerprint, and a per-workspace file manifest (hash per path) enables
incremental re-indexing.
"""

import os
import json
import hashlib
import chromadb
from typing import List, Dict, Any, Optional

from backend.core.config import settings
from backend.rag.embeddings import Embeddings


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.DB_DIR)
        self.embeddings = Embeddings()

    # ── keys & naming ─────────────────────────────────────────────────────────

    def _workspace_hash(self) -> str:
        return hashlib.md5(os.path.abspath(settings.WORKSPACE_DIR).encode("utf-8")).hexdigest()[:16]

    def _collection_name(self) -> str:
        # Fingerprint suffix isolates dimensionalities: switching embedding
        # providers yields a NEW (empty) collection instead of a corrupt mix.
        fp = hashlib.md5(self.embeddings.fingerprint.encode("utf-8")).hexdigest()[:10]
        return f"repoverse_chunks_{self._workspace_hash()}_{fp}"

    @property
    def collection(self):
        return self.client.get_or_create_collection(
            name=self._collection_name(),
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def _manifest_path(self) -> str:
        return os.path.join(settings.DB_DIR, f"index_manifest_{self._workspace_hash()}.json")

    # ── file manifest (incremental index state) ──────────────────────────────

    def file_manifest(self) -> Dict[str, str]:
        try:
            with open(self._manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_manifest(self, manifest: Dict[str, str]):
        try:
            os.makedirs(settings.DB_DIR, exist_ok=True)
            with open(self._manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"VectorStore: manifest save failed: {e}")

    def sync_manifest(self, current_hashes: Dict[str, str]):
        """Persist the post-index manifest (index_service calls after diffing)."""
        self._save_manifest(current_hashes)

    def paths_matching(self, suffix: str) -> List[str]:
        suffix = (suffix or "").strip().lower().lstrip("./\\")
        if not suffix:
            return []
        keys = self.file_manifest().keys()
        matches = [p for p in keys if p.lower().endswith(suffix)]
        if matches:
            return sorted(matches)
        # Manifest may predate this file; fall back to ids stored in chroma.
        try:
            res = self.collection.get(include=[])
            ids = (res or {}).get("ids") or []
            paths = {i.rsplit("#", 1)[0] for i in ids}
            return sorted(p for p in paths if p.lower().endswith(suffix))
        except Exception:
            return []

    # ── writes ────────────────────────────────────────────────────────────────

    def upsert_file(self, rel_path: str, chunks: List[Dict[str, Any]], content_hash: str,
                    mtime: float = 0.0, size: int = 0):
        """Replace all chunks for one file (embeds internally)."""
        col = self.collection
        try:
            col.delete(where={"path": rel_path})
        except Exception:
            pass
        if not chunks:
            return
        ids, docs, metas = [], [], []
        for idx, ch in enumerate(chunks):
            meta = dict(ch.get("metadata", {}))
            meta["path"] = rel_path
            meta["imports"] = json.dumps(meta.get("imports", []) or [])
            meta["exports"] = json.dumps(meta.get("exports", []) or [])
            ids.append(f"{rel_path}#{idx}")
            docs.append(ch["content"])
            metas.append(meta)
        embeddings = self.embeddings.embed_documents(docs)
        col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    def delete_file(self, rel_path: str):
        try:
            self.collection.delete(where={"path": rel_path})
        except Exception as e:
            print(f"VectorStore: delete_file failed: {e}")

    def clear(self):
        """Drop the collection outright (O(1) vs the old delete-by-ids loop)."""
        try:
            self.client.delete_collection(self._collection_name())
        except Exception:
            pass
        try:
            if os.path.exists(self._manifest_path):
                os.remove(self._manifest_path)
        except OSError:
            pass

    # ── reads ─────────────────────────────────────────────────────────────────

    def count(self) -> int:
        try:
            return int(self.collection.count())
        except Exception:
            return 0

    def load_all_chunks(self) -> List[Dict[str, Any]]:
        results = self.collection.get(include=["documents", "metadatas"])
        out: List[Dict[str, Any]] = []
        if not results or "documents" not in results:
            return out
        docs, metas, ids = results["documents"], results["metadatas"], results["ids"]
        for i in range(len(docs)):
            meta = dict(metas[i] or {})
            for key in ("imports", "exports"):
                try:
                    meta[key] = json.loads(meta.get(key, "[]")) if isinstance(meta.get(key), str) else (meta.get(key) or [])
                except Exception:
                    meta[key] = []
            out.append({"id": ids[i], "content": docs[i], "metadata": meta})
        return out

    def search(self, query: str, limit: int = 5, where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query_vector = self.embeddings.embed_query(query)

        chroma_where = None
        if where:
            if "paths" in where:
                paths = where.get("paths") or []
                if not paths:
                    return []
                chroma_where = {"path": {"$in": paths}}
            else:
                chroma_where = where

        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=chroma_where,
        )

        formatted: List[Dict[str, Any]] = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results else [{}] * len(docs)
            ids = results["ids"][0]
            distances = results.get("distances", [[0.0] * len(docs)])[0]
            for i in range(len(docs)):
                meta = dict(metas[i] or {})
                for key in ("imports", "exports"):
                    try:
                        meta[key] = json.loads(meta[key]) if isinstance(meta.get(key), str) else meta.get(key, [])
                    except Exception:
                        pass
                formatted.append({
                    "id": ids[i],
                    "content": docs[i],
                    "metadata": meta,
                    "score": 1.0 - distances[i],  # cosine similarity
                })
        return formatted

    # Legacy parity: one-shot bulk add without manifest bookkeeping.
    def add_chunks(self, chunks: List[Dict[str, Any]]):
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for ch in chunks:
            rel = ch.get("metadata", {}).get("path", "unknown")
            by_file.setdefault(rel, []).append(ch)
        for rel, group in by_file.items():
            self.upsert_file(rel, group, content_hash="")
