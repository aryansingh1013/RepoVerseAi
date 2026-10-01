"""
Utility helpers shared across all AI Skills.

Key design principles:
  - Minimize LLM token usage by doing static analysis in Python first.
  - Only pass a condensed "workspace skeleton" to the LLM (< 1500 tokens).
  - Results are cached externally by each skill via cache.py.
"""
import os
import ast
import json
from typing import Any, Dict, List, Optional, Tuple


# ── Directories to always skip ──────────────────────────────────────────────
# NOTE: "db" is excluded because RepoVerse stores its own ChromaDB index AND
# db/cloned_repos/<repo> — clones of OTHER universes. Scanning it would mix
# foreign repository content into skill results (universe isolation violation).
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "dist", "build",
    ".venv", "venv", ".env", "env", ".mypy_cache", ".pytest_cache",
    ".repoverse", "coverage", ".next", ".nuxt",
    "db", "cloned_repos", ".freebuff", ".agents", "supabase",
}

CODE_EXTENSIONS = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript/React",
    ".js": "JavaScript", ".jsx": "JavaScript/React", ".go": "Go",
    ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".cpp": "C++", ".c": "C", ".swift": "Swift",
    ".kt": "Kotlin", ".vue": "Vue", ".svelte": "Svelte",
}

CONFIG_FILES = [
    "package.json", "pyproject.toml", "requirements.txt",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "Makefile", "docker-compose.yml", "Dockerfile",
    ".eslintrc.json", "tsconfig.json", "vite.config.ts",
    "next.config.js", "tailwind.config.js"
]


# ── Static workspace scanner ─────────────────────────────────────────────────

def safe_walk(workspace_dir: str):
    """
    Unified workspace walker used by ALL skills so every skill sees exactly
    the same universe scope: SKIP_DIRS + hidden dirs filtered, files filtered
    by allow-listed extensions only, and unreadable dirs surfaced as a
    collected warning instead of being silently swallowed.

    Yields (root_rel, files) where root_rel is the path relative to the
    workspace and files is a list of file names (not full paths).
    """
    warnings: List[str] = []

    for root, dirs, filenames in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        rel_root = os.path.relpath(root, workspace_dir).replace("\\", "/")
        try:
            names = os.listdir(root)
        except OSError as e:
            warnings.append(f"Unreadable directory {rel_root}: {e}")
            continue
        keep = []
        for fname in names:
            fpath = os.path.join(root, fname)
            try:
                if not os.path.isfile(fpath):
                    continue
                if os.path.getsize(fpath) > 1_500_000:  # skip huge/generated files
                    continue
            except OSError:
                warnings.append(f"Unreadable file {os.path.join(rel_root, fname)}")
                continue
            keep.append(fname)
        yield rel_root, keep

    for w in warnings:
        print(f"[SKILL][WARN] {w}")


def scan_workspace(workspace_dir: str) -> Dict[str, Any]:
    """
    Walks the workspace directory tree and collects lightweight metadata:
    file counts, language distribution, entry points, and key config files.
    Returns a dict suitable for building LLM prompts.
    """
    files_by_lang: Dict[str, List[str]] = {}
    total_files = 0
    entry_points: List[str] = []
    config_found: Dict[str, bool] = {}
    dir_tree_lines: List[str] = []

    ENTRY_POINT_NAMES = {
        "main.py", "app.py", "server.py", "run.py",
        "index.ts", "index.tsx", "index.js", "main.ts",
        "App.tsx", "App.ts", "App.jsx", "manage.py"
    }

    for cfg in CONFIG_FILES:
        config_found[cfg] = os.path.exists(os.path.join(workspace_dir, cfg))

    # Build a concise directory tree (max 3 levels deep)
    def _tree(path: str, prefix: str, depth: int):
        if depth > 3:
            return
        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return
        for entry in entries:
            if entry in SKIP_DIRS or entry.startswith("."):
                continue
            full = os.path.join(path, entry)
            rel = os.path.relpath(full, workspace_dir)
            is_dir = os.path.isdir(full)
            dir_tree_lines.append(f"{prefix}{'📁 ' if is_dir else '📄 '}{entry}")
            if is_dir:
                _tree(full, prefix + "  ", depth + 1)

    _tree(workspace_dir, "", 1)

    # Walk for stats (shared filtered walker — universe-isolated)
    for root_rel, filenames in safe_walk(workspace_dir):
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in CODE_EXTENSIONS:
                lang = CODE_EXTENSIONS[ext]
                files_by_lang.setdefault(lang, [])
                rel_path = fname if root_rel == "." else f"{root_rel}/{fname}"
                files_by_lang[lang].append(rel_path)
                total_files += 1
                if fname in ENTRY_POINT_NAMES:
                    entry_points.append(rel_path)

    languages = {lang: len(paths) for lang, paths in files_by_lang.items()}

    return {
        "workspace_dir": workspace_dir,
        "repo_name": os.path.basename(workspace_dir),
        "total_files": total_files,
        "languages": languages,
        "entry_points": entry_points[:8],
        "dir_tree": "\n".join(dir_tree_lines[:80]),
        "config_found": {k: v for k, v in config_found.items() if v},
        "files_by_lang": {lang: paths[:5] for lang, paths in files_by_lang.items()},
    }


def validate_workspace(workspace_dir: Optional[str]) -> Tuple[bool, str]:
    """
    Universe-context validation for skill execution.
    Returns (ok, error_code). Never falls back to another directory.
    """
    if not workspace_dir or not str(workspace_dir).strip():
        return False, "NO_UNIVERSE_SELECTED"
    if not os.path.isdir(workspace_dir):
        return False, "WORKSPACE_NOT_FOUND"
    return True, ""


def build_workspace_skeleton(workspace_dir: str, scan: Optional[Dict] = None) -> str:
    """
    Builds a condensed text representation of the workspace for LLM prompts.
    Kept under ~1000 tokens on purpose.
    """
    if scan is None:
        scan = scan_workspace(workspace_dir)

    parts = [
        f"Repository: {scan['repo_name']}",
        f"Total source files: {scan['total_files']}",
        f"Languages: {', '.join(f'{l} ({n} files)' for l, n in scan['languages'].items())}",
        f"Entry points: {', '.join(scan['entry_points']) or 'none detected'}",
        f"Config files present: {', '.join(scan['config_found'].keys()) or 'none'}",
        "",
        "Directory structure (top 3 levels):",
        scan["dir_tree"][:1500],
    ]

    # Append sample file paths per language
    for lang, paths in scan["files_by_lang"].items():
        parts.append(f"\nSample {lang} files: {', '.join(paths[:4])}")

    return "\n".join(parts)


# ── README reader ────────────────────────────────────────────────────────────

def read_readme(workspace_dir: str) -> str:
    for name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
        path = os.path.join(workspace_dir, name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()[:3000]
            except Exception:
                pass
    return ""


# ── LLM-powered analysis ─────────────────────────────────────────────────────

class SkillLLMError(Exception):
    """Raised when the LLM layer cannot fulfil a skill request.

    Carries a machine-readable code so the API can return structured errors
    instead of silently degrading (master prompt §11/§12).
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _extract_json(raw: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from a raw LLM response."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw[3:]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Find the outermost JSON object embedded in the text
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def check_llm_status() -> Dict[str, Any]:
    """
    Real capability probe for the local-first LLM stack.
    Pings Ollama directly (not through the generation path) and reports
    whether the configured default model is actually available.
    Used by /api/llm/status and the frontend status bar.
    """
    from backend.core.config import settings as _s

    endpoint = (_s.OLLAMA_ENDPOINT or "").replace("/v1", "")
    result = {
        "provider": "ollama",
        "endpoint": endpoint,
        "connected": False,
        "model": _s.OLLAMA_DEFAULT_MODEL,
        "model_available": False,
        "error": None,
    }
    try:
        import requests
        resp = requests.get(f"{endpoint}/api/tags", timeout=3)
        resp.raise_for_status()
        result["connected"] = True
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        base = _s.OLLAMA_DEFAULT_MODEL.split(":")[0]
        result["model_available"] = any(
            m == _s.OLLAMA_DEFAULT_MODEL or m.split(":")[0] == base
            for m in models
        )
        if not result["model_available"]:
            result["error"] = (
                f"Ollama is running, but model '{_s.OLLAMA_DEFAULT_MODEL}' "
                f"is unavailable. Available: {models or 'none'}. Run: ollama pull {_s.OLLAMA_DEFAULT_MODEL}"
            )
    except Exception as e:
        result["error"] = f"Ollama is not reachable at {endpoint}: {e}"
    return result


def analyze_with_llm(
    skill_name: str,
    task_prompt: str,
    result_schema_hint: str,
    workspace_dir: str,
    scan: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Calls the LLM with a condensed workspace skeleton and a task-specific prompt.
    Returns parsed JSON matching the skill's result_schema.
    Uses json_mode to enforce structured output.
    Raises SkillLLMError with a structured code when generation fails —
    callers must NOT cache or mask these failures (master prompt §11/§12/§22).
    Token budget: ~800 skeleton + ~300 prompt overhead = ~1100 tokens per call.
    """
    from backend.llm.model_router import model_router

    skeleton = build_workspace_skeleton(workspace_dir, scan)

    system_message = (
        "You are an expert software architect analyzing a code repository. "
        "You MUST respond with ONLY valid JSON — no markdown fences, no prose. "
        f"Return a JSON object matching this schema: {result_schema_hint}"
    )

    user_message = (
        f"Analyze this repository and {task_prompt}\n\n"
        f"=== Repository Context ===\n{skeleton}"
    )

    response = model_router.generate(
        task="analysis",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        json_mode=True,
    )

    # ── Surface real LLM failures instead of masking them ────────────────
    if getattr(response, "status", "") != "success":
        err = (getattr(response, "error_message", "") or "unknown error").lower()
        if "connection" in err or "refused" in err or "timeout" in err or "timed out" in err:
            code = "OLLAMA_UNAVAILABLE"
            msg = (
                "Ollama is not reachable. Start it with `ollama serve` and confirm "
                "the model is pulled (`ollama list`)."
            )
        elif "404" in err or "not found" in err:
            code = "MODEL_MISSING"
            msg = (
                f"Ollama is running, but model '{settings.OLLAMA_DEFAULT_MODEL}' is unavailable. "
                f"Run: ollama pull {settings.OLLAMA_DEFAULT_MODEL}"
            )
        else:
            code = "LLM_GENERATION_FAILED"
            msg = f"All LLM providers failed. Last error: {response.error_message}"
        print(f"[SKILL] {skill_name}: LLM failure [{code}] {msg}")
        raise SkillLLMError(code, msg)

    parsed = _extract_json(getattr(response, "response", "") or "")
    if parsed is None:
        raw_preview = (getattr(response, "response", "") or "")[:200]
        print(f"[SKILL] {skill_name}: JSON parse failed. Raw: {raw_preview}")
        raise SkillLLMError(
            "JSON_PARSE_FAILED",
            f"LLM returned malformed JSON for skill '{skill_name}'. Raw: {raw_preview}",
        )
    return parsed
