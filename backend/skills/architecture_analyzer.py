"""
Architecture Analyzer — LLM-powered with condensed workspace skeleton.
Called once, cached permanently until user clears cache.
~1100 tokens per first run.
"""
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import analyze_with_llm, scan_workspace, SkillLLMError


class ArchitectureAnalyzerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Architecture Analyzer"

    @property
    def description(self) -> str:
        return "Generates system architecture layer descriptions and a Mermaid structural diagram for the active repo."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "layers": {"type": "array", "items": {"type": "object"}},
                "diagram": {"type": "string"}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        cached = get_cached("architecture", workspace_dir)
        if cached:
            return cached

        scan = scan_workspace(workspace_dir)
        schema_hint = (
            '{"description": "string", '
            '"layers": [{"name": "string", "description": "string"}], '
            '"diagram": "mermaid_graph_string"}'
        )

        try:
            result = analyze_with_llm(
                "architecture",
                (
                    "identify the main architectural layers of this repository and produce: "
                    "1) a `description` (2 sentences), "
                    "2) a `layers` array (up to 6 layers, each with `name` and `description`), "
                    "3) a `diagram` field containing a valid Mermaid `graph TD` diagram of the layers."
                ),
                schema_hint,
                workspace_dir,
                scan,
            )
        except SkillLLMError:
            # Never cache LLM failures — re-raise so the API returns a structured
            # error and the user can retry once Ollama is back (§12/§22).
            raise

        # Basic schema validation — normalize repairable shapes, never fake data
        if not isinstance(result.get("layers"), list):
            result["layers"] = []
        if not isinstance(result.get("description"), str):
            result["description"] = ""
        if not isinstance(result.get("diagram"), str) or not result.get("diagram"):
            result["diagram"] = "graph TD\n  A[Repository] --> B[Layers]"

        set_cached("architecture", workspace_dir, result)
        return result


skill_registry.register("architecture", ArchitectureAnalyzerSkill())
