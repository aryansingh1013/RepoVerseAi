"""
Learning Mode — LLM-generated onboarding lessons based on the actual repo.
Called once, cached permanently.
~1100 tokens per first run.
"""
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import analyze_with_llm, scan_workspace, SkillLLMError


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

        try:
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
        except SkillLLMError:
            # Never cache LLM failures — surface structured error instead (§12/§22)
            raise

        # Schema validation — normalize shapes; do NOT fabricate placeholder lessons
        result.setdefault("lessons", [])
        result.setdefault("quiz", [])
        result["lessons"] = [l for l in result["lessons"] if isinstance(l, dict) and l.get("title")]
        result["quiz"] = [q for q in result["quiz"] if isinstance(q, dict) and q.get("question")]

        if not result["lessons"]:
            # LLM succeeded but produced nothing usable — report honestly, don't cache
            raise SkillLLMError(
                "EMPTY_LLM_RESULT",
                "Learning Mode received a valid LLM response but no usable lessons. Try re-running the skill.",
            )

        set_cached("learning", workspace_dir, result)
        return result


skill_registry.register("learning", LearningModeSkill())
