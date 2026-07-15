"""
Performance Review — static file-size and complexity heuristics + LLM insights.
Scans for large files, deeply nested code, and missing async patterns.
LLM called once for improvement suggestions (then cached).
"""
import os
import ast
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import scan_workspace, SKIP_DIRS, analyze_with_llm


class PerformanceReviewSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Performance Review"

    @property
    def description(self) -> str:
        return "Detects large files, deep nesting, and synchronous blocking calls; suggests optimizations."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "optimizations": {"type": "array"},
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("performance", workspace_dir)
        if cached:
            return cached

        optimizations: List[Dict[str, str]] = []

        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, workspace_dir).replace("\\", "/")

                # Large file check (> 500 lines)
                if fname.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        line_count = len(content.split("\n"))
                        if line_count > 500:
                            optimizations.append({
                                "impact": "MEDIUM",
                                "file": rel,
                                "issue": f"File is {line_count} lines — large files are hard to maintain.",
                                "suggestion": "Consider splitting into smaller, focused modules."
                            })
                    except Exception:
                        pass

                # Python-specific: sync blocking patterns
                if fname.endswith(".py"):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            source = f.read()
                        tree = ast.parse(source)

                        for node in ast.walk(tree):
                            # Detect sync sleep in async context
                            if isinstance(node, ast.AsyncFunctionDef):
                                for child in ast.walk(node):
                                    if isinstance(child, ast.Call):
                                        func = child.func
                                        if isinstance(func, ast.Attribute) and func.attr == "sleep":
                                            if isinstance(func.value, ast.Name) and func.value.id == "time":
                                                optimizations.append({
                                                    "impact": "HIGH",
                                                    "file": rel,
                                                    "issue": f"`time.sleep()` in async function `{node.name}` blocks the event loop.",
                                                    "suggestion": "Replace with `await asyncio.sleep()`."
                                                })

                            # Deeply nested loops (> 3 levels)
                            if isinstance(node, (ast.For, ast.While)):
                                depth = _nest_depth(node)
                                if depth > 3:
                                    optimizations.append({
                                        "impact": "MEDIUM",
                                        "file": rel,
                                        "issue": f"Loop nesting depth of {depth} detected — high complexity.",
                                        "suggestion": "Refactor using helper functions or list comprehensions."
                                    })
                    except Exception:
                        pass

                if len(optimizations) >= 30:
                    break

        optimizations = optimizations[:30]

        # LLM for 3 high-level optimization insights
        scan = scan_workspace(workspace_dir)
        issue_count = len(optimizations)
        schema_hint = '{"optimizations": [{"impact": "HIGH|MEDIUM|LOW", "file": "string", "issue": "string", "suggestion": "string"}]}'
        llm_result = analyze_with_llm(
            "performance",
            f"suggest 3 high-level performance improvements for this repository (found {issue_count} static issues)",
            schema_hint,
            workspace_dir,
            scan,
        )
        llm_opts = llm_result.get("optimizations", [])
        optimizations = optimizations + llm_opts[:3]

        result = {"optimizations": optimizations}
        set_cached("performance", workspace_dir, result)
        return result


def _nest_depth(node: ast.AST, current: int = 0) -> int:
    max_depth = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.For, ast.While, ast.If)):
            max_depth = max(max_depth, _nest_depth(child, current + 1))
    return max_depth


skill_registry.register("performance", PerformanceReviewSkill())
