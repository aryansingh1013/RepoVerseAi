"""
Learning Mode — LLM-generated onboarding lessons based on the actual repo.
Called once, cached permanently.
~1100 tokens per first run.
"""
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import analyze_with_llm, scan_workspace


class LearningModeSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Learning Mode"

    @property
    def description(self) -> str:
        return "Generates beginner-friendly onboarding lessons and a quiz about the active repository."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lessons": {"type": "array"},
                "quiz": {"type": "array"},
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("learning", workspace_dir)
        if cached:
            return cached

        scan = scan_workspace(workspace_dir)
        schema_hint = (
            '{"lessons": [{"title": "string", "content": "string"}], '
            '"quiz": [{"question": "string", "options": ["string"], "answer": "string"}]}'
        )

        result = analyze_with_llm(
            "learning",
            (
                "create 3 beginner-friendly onboarding lessons for a new developer joining this project. "
                "Each lesson must have a `title` and `content` (3-4 sentences). "
                "Also create 3 multiple-choice quiz questions (4 options each) with a correct `answer`."
            ),
            schema_hint,
            workspace_dir,
            scan,
        )

        if "error" in result or not result.get("lessons"):
            result = {
                "lessons": [{"title": "Getting Started", "content": f"This repository '{scan['repo_name']}' contains {scan['total_files']} source files. Explore the directory structure to understand the codebase layout."}],
                "quiz": [{"question": "What is the primary language of this repo?", "options": list(scan["languages"].keys())[:4] or ["Unknown"], "answer": list(scan["languages"].keys())[0] if scan["languages"] else "Unknown"}]
            }

        set_cached("learning", workspace_dir, result)
        return result


skill_registry.register("learning", LearningModeSkill())
