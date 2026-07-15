"""
Repository Overview — static file-system analysis only, 0 LLM tokens.
"""
import os
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import scan_workspace, read_readme


class RepositoryOverviewSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Repository Overview"

    @property
    def description(self) -> str:
        return "Profiles tech stack, language metrics, entry points, and directory layout of the active workspace."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "tech_stack": {"type": "array", "items": {"type": "string"}},
                "entry_points": {"type": "array", "items": {"type": "string"}},
                "main_components": {"type": "array", "items": {"type": "string"}},
                "folders_overview": {"type": "array", "items": {"type": "object"}}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        # Check cache first
        cached = get_cached("overview", workspace_dir)
        if cached:
            return cached

        scan = scan_workspace(workspace_dir)
        readme = read_readme(workspace_dir)

        repo_name = scan["repo_name"]
        lang_summary = ", ".join(f"{l} ({n} files)" for l, n in scan["languages"].items())
        total = scan["total_files"]

        # Derive tech stack from config files found
        tech_stack = list(scan["languages"].keys())
        cfg = scan["config_found"]
        if "package.json" in cfg:
            tech_stack += ["Node.js"]
        if "vite.config.ts" in cfg or "vite.config.js" in cfg:
            tech_stack += ["Vite"]
        if "tailwind.config.js" in cfg:
            tech_stack += ["TailwindCSS"]
        if "tsconfig.json" in cfg:
            tech_stack += ["TypeScript"]
        if "requirements.txt" in cfg or "pyproject.toml" in cfg:
            tech_stack += ["Python (pip)"]
        if "Cargo.toml" in cfg:
            tech_stack += ["Rust (Cargo)"]
        if "go.mod" in cfg:
            tech_stack += ["Go Modules"]
        if "docker-compose.yml" in cfg or "Dockerfile" in cfg:
            tech_stack += ["Docker"]
        if "next.config.js" in cfg:
            tech_stack += ["Next.js"]

        # Derive main top-level folders as component overview
        top_dirs = []
        try:
            for entry in sorted(os.listdir(workspace_dir)):
                if entry.startswith(".") or entry in {"node_modules", "__pycache__", "dist", "build"}:
                    continue
                full = os.path.join(workspace_dir, entry)
                if os.path.isdir(full):
                    inner_count = sum(
                        1 for _, _, fnames in os.walk(full) for f in fnames
                        if not f.startswith(".")
                    )
                    top_dirs.append({
                        "path": f"{entry}/",
                        "description": f"Contains ~{inner_count} files"
                    })
        except Exception:
            pass

        # Use README first paragraph as the summary if available
        readme_first = ""
        if readme:
            for line in readme.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    readme_first = line[:300]
                    break

        summary = readme_first or (
            f"'{repo_name}' is a {total}-file repository spanning {lang_summary}."
        )

        result = {
            "summary": summary,
            "tech_stack": list(dict.fromkeys(tech_stack)),
            "entry_points": scan["entry_points"],
            "main_components": [d["path"] for d in top_dirs[:8]],
            "folders_overview": top_dirs[:8],
        }

        set_cached("overview", workspace_dir, result)
        return result


skill_registry.register("overview", RepositoryOverviewSkill())
