import json
from typing import List
from backend.agent.reasoning_models import Goal, Task

class TaskDecomposer:
    def __init__(self, llm_caller=None):
        self.llm_caller = llm_caller

    def decompose(self, goal: Goal, query: str) -> List[Task]:
        """
        Decomposes query and goal parameters into a sequence of dependent tasks.
        """
        system_prompt = (
            "You are RepoVerse AI Task Decomposer.\n"
            "Break down the user query and goal parameters into a list of logical subtasks with priorities and dependencies.\n"
            "You MUST output a JSON object containing the list of tasks:\n"
            "{\n"
            "  \"tasks\": [\n"
            "    {\n"
            "      \"task_id\": \"task_0\",\n"
            "      \"description\": \"Actionable task description (e.g. read config file)\",\n"
            "      \"dependencies\": [],\n"
            "      \"capabilities_needed\": [\"filesystem_read\"],\n"
            "      \"priority\": 1,\n"
            "      \"expected_output\": \"Description of what task should yield\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "1. Output ONLY raw JSON.\n"
            "2. Map capabilities_needed strictly to abstract capability names (e.g. read_file, git_log, browser_search, terminal_run, python_execute).\n"
            "3. Specify parent dependencies carefully to build a clean Directed Acyclic Graph (DAG)."
        )

        user_prompt = f"Goal Intent: {goal.intent}\nGoal Output: {goal.expected_output}\nUser query: {query}"

        if self.llm_caller:
            response = self.llm_caller([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ], json_mode=True)
            if response:
                try:
                    data = json.loads(response)
                    tasks = []
                    for t in data.get("tasks", []):
                        tasks.append(Task(
                            task_id=t.get("task_id"),
                            description=t.get("description"),
                            dependencies=t.get("dependencies", []),
                            capabilities_needed=t.get("capabilities_needed", []),
                            priority=t.get("priority", 1),
                            expected_output=t.get("expected_output", "")
                        ))
                    return tasks
                except Exception:
                    pass

        # Heuristic Fallback
        tasks = []
        if goal.intent == "comparison":
            tasks.append(Task(
                task_id="task_0",
                description="Fetch related documentation schemas or files",
                dependencies=[],
                capabilities_needed=["browser_search"],
                priority=1,
                expected_output="API specs or docs text"
            ))
            tasks.append(Task(
                task_id="task_1",
                description="Read implementation source code file",
                dependencies=[],
                capabilities_needed=["filesystem_read"],
                priority=1,
                expected_output="Source code file text"
            ))
            tasks.append(Task(
                task_id="task_2",
                description="Perform delta comparison analysis",
                dependencies=["task_0", "task_1"],
                capabilities_needed=[],
                priority=2,
                expected_output="delta comparison logs"
            ))
        elif goal.intent == "debug":
            tasks.append(Task(
                task_id="task_0",
                description="Execute local test suite (pytest) to trace errors",
                dependencies=[],
                capabilities_needed=["terminal_run"],
                priority=1,
                expected_output="test stack trace logs"
            ))
            tasks.append(Task(
                task_id="task_1",
                description="Read defective source code details",
                dependencies=["task_0"],
                capabilities_needed=["filesystem_read"],
                priority=2,
                expected_output="source code snippet"
            ))
            tasks.append(Task(
                task_id="task_2",
                description="Formulate fix strategy",
                dependencies=["task_1"],
                capabilities_needed=[],
                priority=3,
                expected_output="code fix patch"
            ))
        elif goal.intent == "explain":
            tasks.append(Task(
                task_id="task_0",
                description="Read relevant project README and context documentation",
                dependencies=[],
                capabilities_needed=["filesystem_read"],
                priority=1,
                expected_output="project summary text"
            ))
            tasks.append(Task(
                task_id="task_1",
                description="Retrieve file structure layout",
                dependencies=[],
                capabilities_needed=["filesystem_list"],
                priority=1,
                expected_output="galaxy tree layout"
            ))
            tasks.append(Task(
                task_id="task_2",
                description="Analyze architectural flow",
                dependencies=["task_0", "task_1"],
                capabilities_needed=[],
                priority=2,
                expected_output="architecture explanation logs"
            ))
        else: # general
            tasks.append(Task(
                task_id="task_0",
                description="Retrieve codebase files or database schemas",
                dependencies=[],
                capabilities_needed=["filesystem_read"],
                priority=1,
                expected_output="source text files"
            ))

        return tasks
