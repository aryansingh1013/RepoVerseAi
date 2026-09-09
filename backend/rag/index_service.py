"""Incremental workspace indexing (fixes audit finding #5: stale index).

Replaces the old cache short-circuit in ``/api/index`` that served the entire
index from the vector store whenever *any* previously-cached file still
existed — silently skipping every file added or edited after the first index.

New contract:
* every file is content-hashed (sha1); the store keeps a per-file manifest;
* only files whose hash changed are re-chunked, re-embedded and upserted;
* files that vanished are deleted from the store;
* BM25 is always re-fit from the current corpus.

Works with both backends because they share the store API
(file_manifest / upsert_file / delete_file / load_all_chunks / sync_manifest
— sync_manifest only exists on the Chroma store and is guarded).
"""

import os
import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple

ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md",
    ".yaml", ".yml", ".toml", ".txt", ".html", ".css",
    ".prisma", ".sql", ".sh", ".graphql",
    ".go", ".rs", ".java", ".c", ".cpp", ".h",
}
EXCLUDE_DIRS = {
    ".git", "__pycache__", "node_modules", ".gemini",
    "venv", ".venv", "db", "dist", "build", ".agents",
    ".vscode", ".idea", ".next", ".turbo",
}
EXCLUDE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    ".gitignore", ".env", "tsconfig.tsbuildinfo",
}
MAX_FILE_BYTES = 150_000


def hash_file(path: str) -> Optional[str]:
    """sha1 of file bytes, or None if unreadable/too large to index."""
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return None
        digest = hashlib.sha1()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return None


def walk_workspace(workspace: str) -> List[str]:
    """Relative POSIX paths of indexable files."""
    rel_paths: List[str] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            if name in EXCLUDE_FILES:
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            rel = os.path.relpath(os.path.join(root, name), workspace).replace(os.sep, "/")
            rel_paths.append(rel)
    return rel_paths


def sync_index(
    workspace: str,
    store: Any,
    chunk_builder: Any,
    retriever: Any,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Incrementally align the store with the workspace. Returns stats."""
    stats = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0, "chunks": 0, "files": 0, "errors": []}

    manifest: Dict[str, str] = dict(store.file_manifest() or {})
    current: Dict[str, str] = {}
    for rel in walk_workspace(workspace):
        h = hash_file(os.path.join(workspace, rel))
        if h is not None:
            current[rel] = h
    stats["files"] = len(current)

    to_add = [p for p in current if p not in manifest]
    to_update = [p for p in current if p in manifest and manifest[p] != current[p]]
    to_remove = [p for p in manifest if p not in current]
    stats["pending"] = len(to_add) + len(to_update)

    new_manifest = dict(manifest)

    for rel in to_remove:
        try:
            store.delete_file(rel)
            stats["removed"] += 1
            new_manifest.pop(rel, None)
        except Exception as e:
            print(f"IndexService: failed to remove {rel}: {e}")

    aborted = False
    for rel in to_add + to_update:
        if aborted:
            break
        full = os.path.join(workspace, rel)
        try:
            chunks = chunk_builder.build_chunks(full, workspace)
            st = os.stat(full)
            store.upsert_file(rel, chunks, current[rel], mtime=st.st_mtime, size=st.st_size)
            stats["updated" if rel in manifest else "added"] += 1
            stats["chunks"] += len(chunks)
            new_manifest[rel] = current[rel]  # manifest only records SUCCEEDED files
            if progress_cb:
                progress_cb({"file": rel, "stats": dict(stats)})
        except Exception as e:
            # First failure is usually systemic (no embedding provider) — record
            # it so the endpoint surfaces a clear 500 instead of fake "success",
            # and stop hammering the provider per-file.
            msg = f"failed to index {rel}: {e}"
            print(f"IndexService: {msg}")
            if len(stats["errors"]) < 5:
                stats["errors"].append(msg[:400])
            if (stats["added"] + stats["updated"]) == 0:
                aborted = True  # provider down; abort, keep old manifest for retry

    # Re-fit BM25 over the authoritative corpus (both store backends expose it).
    try:
        corpus = store.load_all_chunks()
        if callable(getattr(retriever, "fit_bm25", None)):
            retriever.fit_bm25(corpus)
        stats["chunks"] = len(corpus)
    except Exception as e:
        print(f"IndexService: BM25 refit failed: {e}")

    # Chroma keeps its manifest on disk; Supabase persists per-file rows in the
    # upsert itself, so sync_manifest is optional. Persist only files that
    # actually succeeded so failed files retry on the next run.
    if callable(getattr(store, "sync_manifest", None)):
        try:
            store.sync_manifest(new_manifest)
        except Exception as e:
            print(f"IndexService: manifest persist failed: {e}")

    return stats
