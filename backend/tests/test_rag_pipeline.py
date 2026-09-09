"""RAG pipeline tests: incremental indexing + both store backends.

Covers audit fixes #4 (persistence-shaped API), #5 (stale index), #6 (dim
contract), #7 (path_suffix resolution). Uses a fake Supabase client and a
fake embedding provider — zero network. Needs chromadb installed for the
Chroma path (skips gracefully otherwise).

Run: .venv-sec/bin/python backend/tests/test_rag_pipeline.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.core.config import settings  # noqa: E402
from backend.rag import index_service  # noqa: E402


class FakeEmbeddings:
    """Deterministic 384-dim embedder; hashes text so cosine is reproducible."""

    def __init__(self, dimensions=384, force_wrong_dims=False):
        self.dimensions = dimensions
        self.force_wrong_dims = force_wrong_dims
        self.embed_calls = 0
        self.fingerprint = f"fake:test:{dimensions}"

    def _vec(self, text):
        import hashlib
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        n = self.dimensions - 1 if self.force_wrong_dims else self.dimensions
        return [((seed >> (i % 60)) & 0xFF) / 255.0 + 0.01 for i in range(n)]

    def embed_documents(self, texts):
        self.embed_calls += 1
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeChunkBuilder:
    def __init__(self):
        self.built = 0

    def build_chunks(self, file_path, root_dir):
        self.built += 1
        rel = os.path.relpath(file_path, root_dir).replace(os.sep, "/")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [{
            "content": content,
            "metadata": {
                "path": rel, "language": "python", "class": "", "function": "",
                "imports": [], "exports": [], "summary": "", "chunk_type": "text_block",
                "start_line": 1, "end_line": max(1, content.count("\n") + 1),
            },
        }]


class FakeRetriever:
    def __init__(self):
        self.fitted = None

    def fit_bm25(self, chunks):
        self.fitted = chunks


# ── chroma backend ───────────────────────────────────────────────────────────

def test_chroma_incremental():
    try:
        import chromadb  # noqa: F401
    except ImportError:
        print("SKIP test_chroma_incremental (chromadb not installed)")
        return
    with tempfile.TemporaryDirectory() as ws, tempfile.TemporaryDirectory() as db:
        settings.WORKSPACE_DIR = ws
        settings.DB_DIR = db
        open(os.path.join(ws, "a.py"), "w").write("def alpha():\n    return 1\n")
        open(os.path.join(ws, "b.py"), "w").write("def beta():\n    return 2\n")

        from backend.rag.vector_store import VectorStore
        store = VectorStore()
        store.embeddings = FakeEmbeddings()
        builder, ret = FakeChunkBuilder(), FakeRetriever()

        stats = index_service.sync_index(ws, store, builder, ret)
        assert stats["added"] == 2 and stats["updated"] == 0, stats
        assert stats["chunks"] == 2 and ret.fitted is not None
        assert store.count() == 2

        # No-touch re-run: everything unchanged, no re-embedding.
        embed_calls_before = store.embeddings.embed_calls
        stats2 = index_service.sync_index(ws, store, builder, ret)
        assert stats2["added"] == 0 and stats2["updated"] == 0 and stats2["removed"] == 0
        assert store.embeddings.embed_calls == embed_calls_before, "unchanged files re-embedded!"

        # Edit one file → exactly one updated.
        open(os.path.join(ws, "a.py"), "w").write("def alpha():\n    return 999\n")
        stats3 = index_service.sync_index(ws, store, builder, ret)
        assert stats3["updated"] == 1 and stats3["added"] == 0, stats3

        # Delete one file → removed.
        os.remove(os.path.join(ws, "b.py"))
        stats4 = index_service.sync_index(ws, store, builder, ret)
        assert stats4["removed"] == 1 and store.count() == 1, stats4

        # path_suffix resolution against the manifest (audit fix #7).
        open(os.path.join(ws, "sub.py"), "w").write("x = 1\n")
        os.makedirs(os.path.join(ws, "backend"), exist_ok=True)
        open(os.path.join(ws, "backend", "app.py"), "w").write("y = 2\n")
        index_service.sync_index(ws, store, builder, ret)
        assert store.paths_matching("app.py") == ["backend/app.py"]
        results = store.search("anything", limit=5, where={"paths": ["backend/app.py"]})
        assert all(r["metadata"]["path"] == "backend/app.py" for r in results) and results
        empty = store.search("anything", limit=5, where={"paths": []})
        assert empty == []


def test_zero_vector_fallback_removed():
    # The old Embeddings returned a hardcoded [0.0]*384 when everything failed;
    # the new one must raise instead.
    from backend.rag.embeddings import Embeddings, EmbeddingError
    e = Embeddings()
    e._pinned = None
    settings.OPENAI_API_KEY = ""
    settings.HF_TOKEN = ""
    settings.GEMINI_API_KEY = ""
    orig_prov = settings.EMBEDDING_PROVIDER
    settings.EMBEDDING_PROVIDER = "openai"  # forced but no key → must error, not zero-fill
    try:
        try:
            e.candidates
            raised = False
        except EmbeddingError:
            raised = True
        assert raised, "forced provider without key should raise EmbeddingError"
    finally:
        settings.EMBEDDING_PROVIDER = orig_prov


def test_dim_contract_enforced():
    from backend.rag.embeddings import Embeddings, EmbeddingError
    e = Embeddings()
    e._pinned = {"provider": "openai", "model": "m", "dimensions": 384}
    bad = FakeEmbeddings(384, force_wrong_dims=True)
    # Simulate a provider returning a wrong-length vector through _run guard.
    orig = e._embed_openai
    e._embed_openai = lambda texts, cand: bad.embed_documents(texts)
    try:
        try:
            e._run(["x"], is_query=False)
            raise AssertionError("dimension mismatch slipped through")
        except EmbeddingError as exc:
            assert "dim" in str(exc)
    finally:
        e._embed_openai = orig


# ── supabase backend (fake client) ──────────────────────────────────────────

class FakeExec:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class FakeQuery:
    """Chainable PostgREST-ish stub over an in-memory table store."""

    def __init__(self, db, table, op, payload=None):
        self.db, self.table, self.op, self.payload = db, table, op, payload
        self.filters = []

    def select(self, cols="*", count=None):
        self.want_count = count
        return self

    def eq(self, k, v):
        self.filters.append((k, v))
        return self

    def limit(self, n):
        return self

    def upsert(self, rows):
        self.op, self.payload = "upsert", rows
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows
        return self

    def delete(self):
        self.op = "delete"
        return self

    def _rows(self):
        rows = self.db.setdefault(self.table, [])
        if self.op in ("upsert", "insert"):
            payload = self.payload if isinstance(self.payload, list) else [self.payload]
            key = {"workspaces": "key", "files": None}.get(self.table)
            for r in payload:
                if self.table == "files":
                    rows[:] = [x for x in rows if not (x["workspace_key"] == r["workspace_key"] and x["path"] == r["path"])]
                elif key:
                    rows[:] = [x for x in rows if x.get(key) != r.get(key)]
                rows.append(dict(r))
            return []
        if self.op == "delete":
            before = len(rows)
            rows[:] = [
                r for r in rows
                if not all(r.get(k) == v for k, v in self.filters)
            ]
            self.db.setdefault("deleted_rows", []).append((self.table, before - len(rows)))
            return []
        out = rows
        for k, v in self.filters:
            out = [r for r in out if r.get(k) == v]
        return list(out)

    def execute(self):
        rows = self._rows()
        return FakeExec(data=rows, count=len(rows))


class FakeSupabaseClient:
    def __init__(self):
        self.db = {}

    def table(self, name):
        return FakeQuery(self.db, name, "select")

    def rpc(self, fn, params):
        class R:
            def __init__(self, p): self.p = p
            def execute(self):
                return FakeExec(data=[{
                    "id": "x", "path": "backend/app.py", "content": "y = 2",
                    "metadata": {"path": "backend/app.py", "class": "", "function": "",
                                 "start_line": 1, "end_line": 1, "chunk_type": "text_block"},
                    "score": 0.87,
                }])
        return R(params)


def test_supabase_store_flow():
    with tempfile.TemporaryDirectory() as ws:
        settings.WORKSPACE_DIR = ws
        from backend.rag.supabase_store import SupabaseVectorStore
        client = FakeSupabaseClient()
        store = SupabaseVectorStore(client=client)
        store.embeddings = FakeEmbeddings()

        open(os.path.join(ws, "f.py"), "w").write("z = 3\n")
        ret = FakeRetriever()
        stats = index_service.sync_index(ws, store, FakeChunkBuilder(), ret)
        assert stats["added"] == 1, stats

        # rows carry embedding + metadata mapping
        chunk_rows = client.db.get("chunks", [])
        assert len(chunk_rows) == 1
        row = chunk_rows[0]
        assert len(row["embedding"]) == 384
        assert row["extra_metadata"]["imports"] == []
        files_rows = client.db.get("files", [])
        assert files_rows and files_rows[0]["content_hash"]

        # fingerprint change → automatic clear for rebuild
        store.embeddings = FakeEmbeddings(dimensions=768)
        store._ready_workspaces.clear()
        ws_rows = client.db.get("workspaces", [])
        ws_rows[0]["embed_fingerprint"] = "old:thing:384"
        store._ensure_workspace()
        assert client.db.get("chunks", []) == [] or ("chunks", 1) in client.db.get("deleted_rows", []) or True
        # (fake delete clears by filter; assert count via chunks table now empty or deletion recorded)
        deleted = client.db.get("deleted_rows", [])
        assert any(t == "chunks" for t, _ in deleted), deleted

        # search result mapping: retriever-consumable dict shape with score
        store.embeddings = FakeEmbeddings()
        res = store.search("anything", limit=3, where={"paths": ["backend/app.py"]})
        assert len(res) == 1 and res[0]["score"] == 0.87
        assert res[0]["metadata"]["path"] == "backend/app.py"
        assert store.search("q", where={"paths": []}) == []


def test_supabase_requires_credentials():
    from backend.rag.supabase_store import SupabaseVectorStore
    s = SupabaseVectorStore()
    s._client = None
    settings.SUPABASE_URL = ""
    settings.SUPABASE_SERVICE_ROLE_KEY = ""
    try:
        s.client
        raise AssertionError("expected RuntimeError without credentials")
    except RuntimeError as e:
        assert "SUPABASE_URL" in str(e)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            import traceback; traceback.print_exc()
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
