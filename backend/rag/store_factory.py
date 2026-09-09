"""Vector store factory: picks the backend from settings.VECTOR_BACKEND.

* "chroma"    — local PersistentClient (default; desktop/local dev)
* "supabase"  — Postgres + pgvector via Supabase (durable, multi-user-ready)
"""

from backend.core.config import settings


def create_vector_store():
    backend = (getattr(settings, "VECTOR_BACKEND", "chroma") or "chroma").strip().lower()
    if backend in ("supabase", "postgres", "pgvector"):
        from backend.rag.supabase_store import SupabaseVectorStore
        store = SupabaseVectorStore()
        print(f"VectorStore: using Supabase/pgvector backend (workspace={settings.WORKSPACE_DIR})")
        return store
    from backend.rag.vector_store import VectorStore
    store = VectorStore()
    print("VectorStore: using local ChromaDB backend")
    return store
