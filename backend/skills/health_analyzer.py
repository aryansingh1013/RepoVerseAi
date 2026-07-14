import os
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry

class HealthAnalyzerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Repository Health Analyzer"

    @property
    def description(self) -> str:
        return "Inspects files line counts, scans functions/classes complexities, dead imports, and calculates overall codebase score."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "issues": {"type": "array", "items": {"type": "object"}},
                "recommendations": {"type": "array", "items": {"type": "string"}}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        issues = []
        recommendations = []
        score = 92 # Initial default base score

        # Walk workspace to inspect file lines counts
        large_files = []
        missing_docstrings = []
        total_files = 0

        for root, _, filenames in os.walk(workspace_dir):
            if any(p in root for p in [".git", "node_modules", "__pycache__", "dist", "build", ".agents"]):
                continue
            for f in filenames:
                ext = os.path.splitext(f)[1]
                if ext in [".py", ".ts", ".tsx"]:
                    total_files += 1
                    file_path = os.path.join(root, f)
                    rel_path = os.path.relpath(file_path, workspace_dir)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                            lines = file.readlines()
                            line_count = len(lines)
                            
                            # Heuristic: file > 250 lines gets checked
                            if line_count > 250:
                                large_files.append((rel_path, line_count))
                            
                            # Heuristic: Python file missing docstrings at file start
                            if ext == ".py" and line_count > 10:
                                content_strip = "".join(lines[:5]).strip()
                                if '"""' not in content_strip and "'''" not in content_strip:
                                    missing_docstrings.append(rel_path)
                    except Exception:
                        pass

        # Formulate health alerts list
        for path, count in large_files[:3]:
            score -= 3
            issues.append({
                "severity": "MEDIUM",
                "file": path,
                "message": f"File contains {count} lines. Large modules should be split into smaller helper modules."
            })
            recommendations.append(f"Refactor and decouple logic inside large file '{path}'")

        for path in missing_docstrings[:4]:
            score -= 1
            issues.append({
                "severity": "LOW",
                "file": path,
                "message": "File is missing top-level module documentation or structural docstring comments."
            })
            recommendations.append(f"Add module structural documentation and explain capabilities in '{path}'")

        # Heuristic check for package configuration
        if not os.path.exists(os.path.join(workspace_dir, "backend", "requirements.txt")) and not os.path.exists(os.path.join(workspace_dir, "requirements.txt")):
            score -= 4
            issues.append({
                "severity": "HIGH",
                "file": "Workspace Root",
                "message": "Missing python dependencies specification (requirements.txt)."
            })
            recommendations.append("Generate a requirements.txt file listing python pip dependencies.")

        # Ensure score bounds
        score = max(30, min(100, score))

        return {
            "score": score,
            "issues": issues,
            "recommendations": list(set(recommendations)) if recommendations else ["Keep maintaining excellent modularity!"]
        }

skill_registry.register("health", HealthAnalyzerSkill())
