from typing import List, Dict, Any
from backend.agent.reasoning_models import Goal, Task, ExecutionMemory

class ExecutionMemoryTracker:
    def __init__(self):
        self.history: List[ExecutionMemory] = []

    @staticmethod
    def compile_reasoning_trace(goal: Goal, tasks: List[Task], reflection_history: List[str]) -> List[str]:
        """
        Builds a high-level reasoning summary for the user without exposing internal chain of thought.
        """
        trace = []
        
        # 1. Goal intent
        intent_map = {
            "explain": "Understood goal: Explain architecture and code flows.",
            "debug": "Understood goal: Root cause debugging and fix formulation.",
            "comparison": "Understood goal: Dynamic documentation-to-source comparison.",
            "refactor": "Understood goal: Code refactoring and modification patch draft.",
            "general": "Understood goal: Semantic repository inquiry."
        }
        trace.append(intent_map.get(goal.intent, f"Understood request goal as '{goal.intent}'."))

        # 2. Tasks breakdown
        trace.append(f"Decomposed requirements into {len(tasks)} target subtasks.")

        # 3. Execution metrics
        succeeded_tasks = [t for t in tasks if t.status == "success"]
        failed_tasks = [t for t in tasks if t.status == "failed"]
        
        if succeeded_tasks:
            caps = []
            for t in succeeded_tasks:
                caps.extend(t.capabilities_needed)
            if caps:
                trace.append(f"Successfully executed planned capabilities: {', '.join(list(set(caps)))}.")
            else:
                trace.append(f"Completed {len(succeeded_tasks)} analytical subtasks.")
                
        if failed_tasks:
            trace.append(f"Warning: Tool execution failed for tasks: {[t.task_id for t in failed_tasks]}.")

        # 4. Reflection logs
        for refl in reflection_history:
            trace.append(f"Reflection checkpoint: {refl}")

        return trace

    def save_run(self, goal: Goal, tasks: List[Task], execution_time_ms: float, trace: List[str]):
        run_record = ExecutionMemory(
            goal=goal,
            tasks=tasks,
            results=[],
            failures=[t.task_id for t in tasks if t.status == "failed"],
            execution_time_ms=execution_time_ms,
            reasoning_trace=trace
        )
        self.history.append(run_record)
        print(f"Memory: Recorded run trace of {len(trace)} steps. Latency: {execution_time_ms:.1f}ms.")
