from typing import List, Dict, Set
from backend.agent.reasoning_models import Task

class DependencyGraphResolver:
    @staticmethod
    def resolve_parallel_groups(tasks: List[Task]) -> List[List[str]]:
        """
        Builds a dependency graph and returns a list of execution layers (groups of task_ids)
        that can be run concurrently.
        """
        # Graph nodes and mapping
        task_map = {t.task_id: t for t in tasks}
        
        # Build adjacency list and calculate in-degrees
        # Graph: node -> set of nodes that depend on it
        adj: Dict[str, Set[str]] = {t.task_id: set() for t in tasks}
        in_degree: Dict[str, int] = {t.task_id: 0 for t in tasks}

        for t in tasks:
            for dep in t.dependencies:
                # dep must run before t
                if dep in adj:
                    adj[dep].add(t.task_id)
                    in_degree[t.task_id] += 1
                else:
                    # Parent dependency not declared as task, ignore or log
                    pass

        # Find layers for parallel execution (Kahn's algorithm adaptation)
        # Find all nodes with 0 in-degree (independent starting tasks)
        current_layer = [tid for tid, deg in in_degree.items() if deg == 0]
        parallel_groups = []

        visited_count = 0
        while current_layer:
            parallel_groups.append(current_layer)
            visited_count += len(current_layer)
            
            next_layer = []
            for node in current_layer:
                for neighbor in adj[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_layer.append(neighbor)
            current_layer = next_layer

        # If we didn't visit all nodes, there is a cycle!
        if visited_count < len(tasks):
            # Cyclic dependency found. Fallback: put remaining tasks in a sequential loop
            print("DependencyGraph Warning: Cycle detected in tasks! Falling back to sequential execution.")
            remaining = [t.task_id for t in tasks if t.task_id not in [tid for group in parallel_groups for tid in group]]
            for tid in remaining:
                parallel_groups.append([tid])

        return parallel_groups
