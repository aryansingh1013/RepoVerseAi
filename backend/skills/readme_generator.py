"""
README Generator — LLM-powered, uses real README + workspace scan.
Called once, cached permanently.
~1200 tokens per first run (includes existing README text as context).
"""
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import analyze_with_llm, scan_workspace, read_readme, build_workspace_skeleton


class ReadmeGeneratorSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "README Generator"

    @property
    def description(self) -> str:
        return "Auto-generates or improves a README.md for the active repository."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "markdown": {"type": "string"}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("readme", workspace_dir)
        if cached:
            return cached

        from backend.llm.model_router import model_router

        scan = scan_workspace(workspace_dir)
        existing_readme = read_readme(workspace_dir)
        skeleton = build_workspace_skeleton(workspace_dir, scan)

        existing_section = ""
        if existing_readme:
            existing_section = f"\n=== Existing README (use as input, improve it) ===\n{existing_readme[:1500]}"

        system_message = (
            "You are a technical writer generating a professional README.md. "
            "Respond with ONLY the raw Markdown content — no JSON, no code fences around the whole response."
        )
        user_message = (
            f"Generate a comprehensive, well-structured README.md for this repository.\n"
            f"Include sections: Project Overview, Features, Tech Stack, Installation, Usage, Project Structure, Contributing.\n"
            f"Make it accurate and specific to THIS repository — do not use generic placeholder text.\n\n"
            f"=== Repository Context ===\n{skeleton}{existing_section}"
        )

        response = model_router.generate(
            task="analysis",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            json_mode=False,
        )

        markdown = response.response or f"# {scan['repo_name']}\n\nREADME generation failed. Please check your LLM configuration."

        result = {"markdown": markdown}
        set_cached("readme", workspace_dir, result)
        return result


skill_registry.register("readme", ReadmeGeneratorSkill())
