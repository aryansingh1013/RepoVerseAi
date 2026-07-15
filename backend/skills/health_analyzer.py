"""
Health Analyzer — static AST code-quality checks + optional LLM summary.
The bulk of the analysis is done with Python (0 tokens). The LLM is only
used to produce a one-paragraph recommendations summary (cached afterwards).
"""
import os
import ast
import re
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import scan_workspace, SKIP_DIRS, analyze_with_llm


class HealthAnalyzerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Health Analyzer"

    @property
    def description(self) -> str:
        return "Scans for code quality issues (long functions, bare excepts, TODOs) and scores the repository."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "issues": {"type": "array"},
                "recommendations": {"type": "array"},
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("health", workspace_dir)
        if cached:
            return cached

        issues: List[Dict[str, str]] = []

        for root, dirs, files in os.walk(workspace_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, workspace_dir).replace("\\", "/")
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    lines = source.split("\n")

                    # Long lines
                    for i, line in enumerate(lines, 1):
                        if len(line) > 120:
                            issues.append({"severity": "LOW", "file": f"{rel}:{i}", "message": "Line exceeds 120 characters."})
                            if len(issues) > 60:
                                break

                    # TODOs / FIXMEs
                    for i, line in enumerate(lines, 1):
                        if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.IGNORECASE):
                            issues.append({"severity": "LOW", "file": f"{rel}:{i}", "message": f"Found TODO/FIXME marker: {line.strip()[:80]}"})

                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        # Bare except
                        if isinstance(node, ast.ExceptHandler) and node.type is None:
                            issues.append({"severity": "MEDIUM", "file": rel, "message": "Bare `except:` clause catches all exceptions — use specific types."})

                        # Long functions (> 80 lines)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            length = (node.end_lineno or node.lineno) - node.lineno
                            if length > 80:
                                issues.append({"severity": "MEDIUM", "file": rel, "message": f"Function `{node.name}` is {length} lines long — consider breaking it up."})

                        # Missing docstrings on public functions
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not node.name.startswith("_") and not ast.get_docstring(node):
                                issues.append({"severity": "LOW", "file": rel, "message": f"Public function `{node.name}` has no docstring."})

                except Exception:
                    pass

        # Clamp issue list and compute score
        issues = issues[:50]
        high = sum(1 for i in issues if i["severity"] == "HIGH")
        medium = sum(1 for i in issues if i["severity"] == "MEDIUM")
        low = sum(1 for i in issues if i["severity"] == "LOW")
        penalty = high * 10 + medium * 4 + low * 1
        score = max(0, min(100, 100 - penalty))

        # Quick LLM call for recommendations only (condensed prompt)
        scan = scan_workspace(workspace_dir)
        issue_summary = f"{high} high, {medium} medium, {low} low severity issues found."
        schema_hint = '{"recommendations": ["string"]}'
        recs_result = analyze_with_llm(
            "health",
            f"provide 5 concise refactoring recommendations for a repository with score {score}/100 and {issue_summary}",
            schema_hint,
            workspace_dir,
            scan,
        )
        recommendations = recs_result.get("recommendations", [
            "Review bare except blocks and add proper exception handling.",
            "Add docstrings to all public functions.",
            "Break up functions longer than 80 lines.",
            "Resolve all TODO/FIXME markers.",
            "Enforce a linting tool (pylint, ruff, or eslint)."
        ])

        result = {
            "score": score,
            "issues": issues,
            "recommendations": recommendations[:6],
        }

        set_cached("health", workspace_dir, result)
        return result


skill_registry.register("health", HealthAnalyzerSkill())
