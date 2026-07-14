import time
import concurrent.futures
from typing import List, Dict, Any
from backend.agent.reasoning_models import ExecutionPlan, Task
from backend.agent.registry import AgentToolRegistry
from backend.agent.tool_models import ToolResult

class ParallelExecutor:
    def __init__(self, agent_registry: AgentToolRegistry, max_workers: int = 5):
        self.agent_registry = agent_registry
        self.max_workers = max_workers

    def execute_plan(self, plan: ExecutionPlan, steps: List[str]) -> List[Task]:
        """
        Executes the Plan's parallel groups sequentially. Within each group,
        tasks are scheduled and run concurrently.
        """
        task_map = {t.task_id: t for t in plan.tasks}
        
        # Thread function to run a single task
        def run_single_task(task: Task) -> Task:
            task.status = "running"
            start_time = time.perf_counter()
            
            # Aggregate tool execution results for this task
            results = []
            status = "success"
            errors = []
            
            # Execute each capability requested by the task
            for cap_name in task.capabilities_needed:
                try:
                    # Execute capability via standard registry wrapper
                    tool_res: ToolResult = self.agent_registry.execute_agent_capability(cap_name, {})
                    results.append(tool_res.model_dump())
                    if tool_res.status != "success":
                        status = "failed"
                        if tool_res.errors:
                            errors.extend(tool_res.errors)
                except Exception as e:
                    status = "failed"
                    errors.append(f"Subtask execution crash: {e}")
            
            latency = (time.perf_counter() - start_time) * 1000.0
            
            # Update task state
            task.status = status
            task.latency_ms = round(latency, 2)
            task.output_payload = {
                "results": results,
                "errors": errors if errors else None
            }
            return task

        steps.append(f"🧠 Executor: Spawning threads for {len(plan.parallel_groups)} parallel groups...")

        for idx, group in enumerate(plan.parallel_groups, start=1):
            steps.append(f"Executing parallel Group {idx}/{len(plan.parallel_groups)}: {group}...")
            
            # Filter tasks in this group
            group_tasks = [task_map[tid] for tid in group if tid in task_map]
            if not group_tasks:
                continue

            # Run group tasks concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Map futures
                futures = {executor.submit(run_single_task, t): t.task_id for t in group_tasks}
                
                for future in concurrent.futures.as_completed(futures):
                    tid = futures[future]
                    try:
                        updated_task = future.result()
                        # Update mapping
                        task_map[tid] = updated_task
                        steps.append(f"Task '{tid}' finished with status [{updated_task.status}] in {updated_task.latency_ms:.1f}ms.")
                    except Exception as exc:
                        task_map[tid].status = "failed"
                        task_map[tid].output_payload = {"errors": [f"Thread raised exception: {exc}"]}
                        steps.append(f"Task '{tid}' raised an execution exception: {exc}")

        # Return updated tasks list
        return list(task_map.values())
