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
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", "dist", "build",
    ".venv", "venv", ".env", "env", ".mypy_cache", ".pytest_cache",
    ".repoverse", "coverage", ".next", ".nuxt"
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

    # Walk for stats
    for root, dirs, filenames in os.walk(workspace_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in CODE_EXTENSIONS:
                lang = CODE_EXTENSIONS[ext]
                files_by_lang.setdefault(lang, [])
                rel_path = os.path.relpath(os.path.join(root, fname), workspace_dir)
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

    raw = response.response or "{}"
    # Strip any accidental markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[-1].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"analyze_with_llm: JSON parse failed — {e}. Raw:\n{raw[:300]}")
        return {"error": f"JSON parse failed: {e}", "raw": raw[:500]}
