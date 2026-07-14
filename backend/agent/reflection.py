import json
from typing import List, Dict, Any
from backend.agent.reasoning_models import Goal, Task

class ReflectionNode:
    def __init__(self, llm_caller=None):
        self.llm_caller = llm_caller

    def evaluate_coverage(self, goal: Goal, tasks: List[Task], fused_contexts: Dict[str, Any], retries: int) -> Dict[str, Any]:
        """
        Reflects on the quality and completeness of collected contexts.
        Decides if a replanning phase is necessary.
        """
        # Hard limits
        if retries >= 2:
            return {
                "need_replanning": False,
                "confidence": 0.5,
                "reason": "Max re-planning retries hit. Proceeding to generation."
            }

        # 1. Check for failed critical tasks
        failed_tasks = [t.task_id for t in tasks if t.status == "failed"]
        if failed_tasks:
            return {
                "need_replanning": True,
                "confidence": 0.3,
                "reason": f"Execution of subtasks failed: {failed_tasks}. Triggering replanning."
            }

        # 2. Call LLM for logical completeness evaluation
        system_prompt = (
            "You are RepoVerse AI Reflection Node.\n"
            "Analyze the user's target Goal and the collected context data. Decide if the context contains enough information to write an accurate, comprehensive, grounded answer.\n"
            "Respond ONLY with a JSON object:\n"
            "{\n"
            "  \"need_replanning\": bool,\n"
            "  \"confidence_score\": float,\n"
            "  \"reason\": \"Explain your decision\"\n"
            "}"
        )

        user_content = (
            f"Goal: {goal.expected_output}\n"
            f"Collected Contexts: {[c['source'] for c in fused_contexts.get('contexts', [])]}\n"
            f"Tasks Run: {[t.description for t in tasks]}"
        )

        if self.llm_caller:
            response = self.llm_caller([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ], json_mode=True)
            if response:
                try:
                    data = json.loads(response)
                    return {
                        "need_replanning": data.get("need_replanning", False),
                        "confidence": data.get("confidence_score", 1.0),
                        "reason": data.get("reason", "LLM Reflection Completed.")
                    }
                except Exception:
                    pass

        # Heuristic Fallback
        need_replanning = False
        reason = "Heuristic check complete: Sufficient context gathered."
        confidence = 0.9

        # If no contexts loaded
        if not fused_contexts.get("contexts"):
            need_replanning = True
            reason = "No context data could be loaded. Requesting replanning."
            confidence = 0.2

        return {
            "need_replanning": need_replanning,
            "confidence": confidence,
            "reason": reason
        }
