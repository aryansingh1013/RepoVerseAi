from typing import List
from backend.agent.reasoning_models import Goal, Task, ExecutionPlan
from backend.agent.dependency_graph import DependencyGraphResolver

class PlannerV2:
    def __init__(self):
        pass

    def generate_execution_strategy(self, goal: Goal, tasks: List[Task]) -> ExecutionPlan:
        """
        Calculates task execution layers and compiles them into a structured ExecutionPlan.
        """
        # Sort tasks by priority
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)
        
        # Resolve parallel execution groups based on graph dependencies
        parallel_groups = DependencyGraphResolver.resolve_parallel_groups(sorted_tasks)

        # Base confidence calculation based on goal confidence
        confidence = goal.confidence

        return ExecutionPlan(
            goal=goal,
            tasks=sorted_tasks,
            parallel_groups=parallel_groups,
            confidence_score=confidence
        )
