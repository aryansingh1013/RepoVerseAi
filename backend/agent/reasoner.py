import time
from typing import Dict, Any, List
from backend.agent.state import AgentState
from backend.agent.registry import AgentToolRegistry
from backend.agent.goal_analyzer import GoalAnalyzer
from backend.agent.task_decomposer import TaskDecomposer
from backend.agent.planner_v2 import PlannerV2
from backend.agent.parallel_executor import ParallelExecutor
from backend.agent.result_fusion import ResultFusion
from backend.agent.reflection import ReflectionNode
from backend.agent.execution_memory import ExecutionMemoryTracker

class CognitiveReasoner:
    def __init__(self, agent_registry: AgentToolRegistry, llm_caller=None):
        self.agent_registry = agent_registry
        self.llm_caller = llm_caller
        
        # Instantiate subcomponents
        self.goal_analyzer = GoalAnalyzer(self.llm_caller)
        self.task_decomposer = TaskDecomposer(self.llm_caller)
        self.planner = PlannerV2()
        self.parallel_executor = ParallelExecutor(self.agent_registry)
        self.reflection = ReflectionNode(self.llm_caller)
        self.memory = ExecutionMemoryTracker()

    def execute_cognitive_cycle(self, state: AgentState) -> Dict[str, Any]:
        """
        Executes the reasoning cycle: Goal Analyzer -> Task Decomposer ->
        DAG Planner -> Parallel Executor -> Result Fusion -> Reflection -> Memory.
        """
        query = state["query"]
        steps = state.get("agent_steps", [])
        tool_outputs = state.get("tool_outputs", [])
        rag_contexts = state.get("retrieved_contexts", [])

        steps.append("🧠 Cognitive Reasoner: Starting reasoning cycle...")
        start_time = time.perf_counter()

        # 1. Goal Analyzer
        goal = self.goal_analyzer.analyze_goal(query)
        steps.append(f"Goal Analysed: intent='{goal.intent}', risk='{goal.risk_level}', output='{goal.expected_output}'")

        # Loop parameters
        retries = 0
        tasks = []
        reflection_history = []
        fused_results = {}

        while retries < 2:
            # 2. Task Decomposer
            tasks = self.task_decomposer.decompose(goal, query)
            steps.append(f"Decomposed query into {len(tasks)} tasks.")

            # 3. Strategy Planner
            plan = self.planner.generate_execution_strategy(goal, tasks)
            steps.append(f"Execution Strategy: Parallel Groups = {plan.parallel_groups}")

            # 4. Parallel Executor
            executed_tasks = self.parallel_executor.execute_plan(plan, steps)
            tasks = executed_tasks

            # 5. Result Fusion
            fused_results = ResultFusion.fuse_contexts(tasks, rag_contexts)

            # 6. Reflection
            refl_result = self.reflection.evaluate_coverage(goal, tasks, fused_results, retries)
            reflection_history.append(refl_result["reason"])
            steps.append(f"Reflection Check: need_replanning={refl_result['need_replanning']}, reason='{refl_result['reason']}'")

            if not refl_result["need_replanning"]:
                break
                
            retries += 1
            # Adjust query for replanning
            query = f"{query} (Retry context addition: {refl_result['reason']})"

        # 7. Compile Reasoning Trace & Record Memory
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000.0

        trace = self.memory.compile_reasoning_trace(goal, tasks, reflection_history)
        self.memory.save_run(goal, tasks, total_time_ms, trace)

        steps.append(f"🧠 Cognitive Reasoner: Finished cycle in {total_time_ms:.1f}ms.")

        # Serialize tasks for UI timeline representation
        serialized_tasks = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "status": t.status,
                "dependencies": t.dependencies,
                "capabilities": t.capabilities_needed,
                "latency_ms": t.latency_ms
            }
            for t in tasks
        ]

        serialized_goal = {
            "intent": goal.intent,
            "expected_output": goal.expected_output,
            "risk_level": goal.risk_level,
            "confidence": goal.confidence
        }

        return {
            "retrieved_contexts": fused_results.get("contexts", []),
            "agent_steps": steps,
            "reasoning_trace": trace,
            "goal_metadata": serialized_goal,
            "tasks_metadata": serialized_tasks,
            "reflection_status": {
                "confidence": refl_result.get("confidence", 1.0),
                "reason": refl_result.get("reason", "")
            }
        }
