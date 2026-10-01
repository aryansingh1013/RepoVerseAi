"""
Dependency Explorer — pure Python AST parsing, 0 LLM tokens.
Reads all .py and .ts/.tsx files and extracts import statements statically.
Now also detects circular import chains via DFS over the resolved internal
module graph (deterministic — no LLM needed).
"""
import os
import ast
import re
from typing import List, Dict, Any, Set
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import scan_workspace, safe_walk, SKIP_DIRS


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
        parse_errors: List[str] = []
        internal_edges: Dict[str, Set[str]] = {}  # module -> internal modules it imports

        # Pass 1: collect internal module names so import classification is accurate
        internal_modules: Set[str] = set()
        py_files: List[tuple] = []
        ts_files: List[tuple] = []
        for root_rel, filenames in safe_walk(workspace_dir):
            for fname in filenames:
                rel = fname if root_rel == "." else f"{root_rel}/{fname}"
                if fname.endswith(".py"):
                    py_files.append((rel, os.path.join(workspace_dir, root_rel, fname)))
                    internal_modules.add(rel.replace("/", ".").removesuffix(".py"))
                elif fname.endswith((".ts", ".tsx", ".js", ".jsx")):
                    ts_files.append((rel, os.path.join(workspace_dir, root_rel, fname)))

        def _resolve_internal(mod: str) -> bool:
            """True if `mod` resolves to a known internal module.
            Handles both namespaced (`backend.utils`) and flat sibling
            (`utils` → backend/utils.py) import styles."""
            if mod in internal_modules:
                return True
            suffix = "." + mod
            return any(m.endswith(suffix) for m in internal_modules)

        # ── Parse Python files (AST) ────────────────────────────────────
        for rel, fpath in py_files:
            module_name = rel.replace("/", ".").removesuffix(".py")
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
                tree = ast.parse(source)
            except SyntaxError as e:
                parse_errors.append(f"{rel}: SyntaxError {e.msg} (line {e.lineno})")
                continue
            except OSError as e:
                parse_errors.append(f"{rel}: unreadable ({e})")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _resolve_internal(alias.name):
                            internal_edges.setdefault(module_name, set()).add(alias.name)
                            deps_map.append({"source": rel, "target": alias.name, "relation_type": "imports"})
                        else:
                            pkg = alias.name.split(".")[0]
                            external[pkg] = external.get(pkg, 0) + 1
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        is_internal = node.level > 0 or _resolve_internal(node.module)
                        if is_internal:
                            target = ("." * node.level) + (node.module or "")
                            internal_edges.setdefault(module_name, set()).add(node.module)
                            deps_map.append({"source": rel, "target": target, "relation_type": "imports"})
                        else:
                            pkg = node.module.split(".")[0]
                            external[pkg] = external.get(pkg, 0) + 1

        # ── Parse TypeScript/JS files (regex) ───────────────────────────
        ts_internal: Set[str] = set()
        for rel, _ in ts_files:
            base = rel.rsplit(".", 1)[0]
            ts_internal.add(base)
            ts_internal.add(base + "/index")

        for rel, fpath in ts_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
            except OSError as e:
                parse_errors.append(f"{rel}: unreadable ({e})")
                continue
            for m in re.finditer(r'import\s+(?:[^"\']+\s+from\s+)?["\']([^"\']+)["\']', source):
                target = m.group(1)
                if target.startswith("."):
                    deps_map.append({"source": rel, "target": target, "relation_type": "imports"})
                    resolved = os.path.normpath(os.path.join(os.path.dirname(rel), target)).replace("\\", "/")
                    if resolved in ts_internal or (resolved + "/index") in ts_internal:
                        norm = resolved if resolved in ts_internal else resolved + "/index"
                        internal_edges.setdefault(rel.rsplit(".", 1)[0], set()).add(norm)
                else:
                    pkg = target.split("/")[0].lstrip("@")
                    external[pkg] = external.get(pkg, 0) + 1

        # ── Circular dependency detection (DFS over internal graph) ─────
        circular = _find_cycles(internal_edges)

        # Limit output size, but report the true totals so nothing is hidden
        total_relations = len(deps_map)
        deps_map = deps_map[:80]
        top_external = sorted(external.items(), key=lambda x: -x[1])[:25]

        result = {
            "dependencies_map": deps_map,
            "circular_dependencies": circular,
            "external_packages": [{"package": p, "usage_count": c} for p, c in top_external],
            "total_relations": total_relations,
        }
        if parse_errors:
            result["warnings"] = [f"Could not parse {len(parse_errors)} file(s):"] + parse_errors[:5]

        set_cached("dependencies", workspace_dir, result)
        return result


def _find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    """Detect circular import chains via iterative DFS with a color map.
    Deterministic and cheap — no LLM needed."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    cycles: List[List[str]] = []

    for start in list(graph.keys()):
        if color.get(start, BLACK) != WHITE:
            continue
        stack = [(start, iter(sorted(graph.get(start, set()))))]
        color[start] = GRAY
        path = [start]
        while stack:
            node, it = stack[-1]
            advanced = False
            for nxt in it:
                nxt = nxt.replace("/", ".")  # normalize TS paths into module form
                c = color.get(nxt, WHITE)
                if c == GRAY:
                    # Found a cycle: slice path from the first occurrence of nxt
                    try:
                        idx = path.index(nxt)
                        cycle = path[idx:] + [nxt]
                        if cycle not in cycles:
                            cycles.append(cycle)
                    except ValueError:
                        pass
                elif c == WHITE:
                    color[nxt] = GRAY
                    path.append(nxt)
                    stack.append((nxt, iter(sorted(graph.get(nxt, set())))))
                    advanced = True
                    break
            if not advanced:
                stack.pop()
                color[node] = BLACK
                if path and path[-1] == node:
                    path.pop()

    return cycles[:10]  # cap the report; cycle count beyond this is noise


skill_registry.register("dependencies", DependencyExplorerSkill())
