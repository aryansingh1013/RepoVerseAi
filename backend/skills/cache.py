"""
Disk-based cache for skill execution results.
Each workspace gets its own cache file stored in <workspace>/.repoverse/skills_cache.json.
Once a skill has been run for a workspace, the result is served from cache on
subsequent runs — costing zero tokens.
"""
import os
import json
import hashlib
from typing import Any, Optional, Dict


def _cache_path(workspace_dir: str) -> str:
    cache_dir = os.path.join(workspace_dir, ".repoverse")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "skills_cache.json")


def _workspace_hash(workspace_dir: str) -> str:
    """A short hash of the workspace path, used as a cache namespace."""
    return hashlib.md5(workspace_dir.encode()).hexdigest()[:8]


def _load_cache(workspace_dir: str) -> Dict[str, Any]:
    path = _cache_path(workspace_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_cache(workspace_dir: str, data: Dict[str, Any]) -> None:
    path = _cache_path(workspace_dir)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"SkillCache: Failed to write cache — {e}")


def get_cached(slug: str, workspace_dir: str) -> Optional[Dict[str, Any]]:
    """Return cached result for this skill + workspace, or None if not cached."""
    cache = _load_cache(workspace_dir)
    key = f"{slug}:{_workspace_hash(workspace_dir)}"
    result = cache.get(key)
    if result is not None:
        print(f"SkillCache: Cache HIT for '{slug}' — 0 tokens used.")
    return result


def set_cached(slug: str, workspace_dir: str, result: Dict[str, Any]) -> None:
    """Persist the skill result to disk cache."""
    cache = _load_cache(workspace_dir)
    key = f"{slug}:{_workspace_hash(workspace_dir)}"
    cache[key] = result
    _save_cache(workspace_dir, cache)
    print(f"SkillCache: Cached result for '{slug}'.")


def clear_cache(workspace_dir: str, slug: Optional[str] = None) -> None:
    """Clear one skill's cache entry, or the entire workspace cache."""
    if slug is None:
        path = _cache_path(workspace_dir)
        if os.path.exists(path):
            os.remove(path)
        print(f"SkillCache: Full cache cleared for workspace.")
    else:
        cache = _load_cache(workspace_dir)
        key = f"{slug}:{_workspace_hash(workspace_dir)}"
        cache.pop(key, None)
        _save_cache(workspace_dir, cache)
        print(f"SkillCache: Cleared cache for '{slug}'.")
