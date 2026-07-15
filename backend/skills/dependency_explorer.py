"""
Dependency Explorer — pure Python AST parsing, 0 LLM tokens.
Reads all .py and .ts/.tsx files and extracts import statements statically.
"""
import os
import ast
import re
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import scan_workspace, SKIP_DIRS


class DependencyExplorerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Dependency Explorer"

    @property
    def description(self) -> str:
        return "Maps import dependencies between modules using AST parsing — no LLM required."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "dependencies_map": {"type": "array"},
                "circular_dependencies": {"type": "array"},
                "external_packages": {"type": "array"},
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("dependencies", workspace_dir)
        if cached:
            return cached

        deps_map: List[Dict[str, str]] = []
        external: Dict[str, int] = {}
        internal_modules: set = set()

        # ── Parse Python files ──────────────────────────────────────────────
        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, workspace_dir).replace("\\", "/")
                module_name = rel.replace("/", ".").removesuffix(".py")
                internal_modules.add(module_name)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                pkg = alias.name.split(".")[0]
                                external[pkg] = external.get(pkg, 0) + 1
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                pkg = node.module.split(".")[0]
                                if node.level > 0 or pkg in internal_modules or "." in node.module:
                                    deps_map.append({
                                        "source": rel,
                                        "target": node.module,
                                        "relation_type": "imports"
                                    })
                                else:
                                    external[pkg] = external.get(pkg, 0) + 1
                except Exception:
                    pass

        # ── Parse TypeScript/JS files (simple regex) ────────────────────────
        ts_exts = {".ts", ".tsx", ".js", ".jsx"}
        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                if not any(fname.endswith(e) for e in ts_exts):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, workspace_dir).replace("\\", "/")
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    # Match: import X from "Y"  or  import "Y"
                    for m in re.finditer(r'import\s+(?:[^"\']+\s+from\s+)?["\']([^"\']+)["\']', source):
                        target = m.group(1)
                        if target.startswith("."):
                            deps_map.append({
                                "source": rel,
                                "target": target,
                                "relation_type": "imports"
                            })
                        else:
                            pkg = target.split("/")[0].lstrip("@")
                            external[pkg] = external.get(pkg, 0) + 1
                except Exception:
                    pass

        # Limit output size
        deps_map = deps_map[:60]
        top_external = sorted(external.items(), key=lambda x: -x[1])[:25]

        result = {
            "dependencies_map": deps_map,
            "circular_dependencies": [],  # simple AST walk can't easily detect cycles
            "external_packages": [{"package": p, "usage_count": c} for p, c in top_external],
        }

        set_cached("dependencies", workspace_dir, result)
        return result


skill_registry.register("dependencies", DependencyExplorerSkill())
