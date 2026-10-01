"""
README Generator — LLM-powered, uses real README + workspace scan.
Called once, cached permanently.
~1200 tokens per first run (includes existing README text as context).
"""
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry
from backend.skills.cache import get_cached, set_cached
from backend.skills.utils import (
    analyze_with_llm,
    scan_workspace,
    read_readme,
    build_workspace_skeleton,
    SkillLLMError,
)


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

        # ── Surface real LLM failures instead of turning them into a README ──
        if getattr(response, "status", "") != "success":
            err = (getattr(response, "error_message", "") or "unknown error").lower()
            if "connection" in err or "refused" in err or "timeout" in err or "timed out" in err:
                raise SkillLLMError(
                    "OLLAMA_UNAVAILABLE",
                    "Ollama is not reachable. Start it with `ollama serve` and confirm the model is pulled.",
                )
            elif "404" in err or "not found" in err:
                from backend.core.config import settings as _s
                raise SkillLLMError(
                    "MODEL_MISSING",
                    f"Ollama is running, but model '{_s.OLLAMA_DEFAULT_MODEL}' is unavailable. Run: ollama pull {_s.OLLAMA_DEFAULT_MODEL}",
                )
            else:
                raise SkillLLMError(
                    "LLM_GENERATION_FAILED",
                    f"README generation failed. All LLM providers failed. Last error: {response.error_message}",
                )

        markdown = (getattr(response, "response", "") or "").strip()
        # Strip a stray router-error sentence that slipped into an otherwise
        # successful response, plus any leftover thinking blocks, then reject
        # empty output instead of caching a fake README.
        markdown = markdown.replace("Error: All LLM providers in the fallback chain were exhausted.", "")
        import re as _re
        markdown = _re.sub(r"<think>.*?</think>", "", markdown, flags=_re.DOTALL).strip()
        if not markdown:
            raise SkillLLMError(
                "EMPTY_LLM_RESULT",
                "The LLM returned an empty response for README generation. Try re-running the skill.",
            )

        result = {"markdown": markdown}
        set_cached("readme", workspace_dir, result)
        return result


skill_registry.register("readme", ReadmeGeneratorSkill())
