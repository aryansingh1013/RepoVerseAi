from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry

class LearningModeSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Learning Mode"

    @property
    def description(self) -> str:
        return "Teaches developers the codebase layout via structured lessons and interactive quizzes."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lessons": {"type": "array", "items": {"type": "object"}},
                "quiz": {"type": "array", "items": {"type": "object"}}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        lessons = [
            {
                "title": "Onboarding overview & space theme",
                "content": "RepoVerse is structured around a space theme. The codebase hierarchy is mapped to celestial elements: All Repositories is the Universe, the active repository is a Galaxy, folders are Stars, files are Planets, and functions/classes are Moons. The UI visualizes this map alongside AI engineering chat capabilities."
            },
            {
                "title": "Cognitive reasoning layers & state graph",
                "content": "The backend utilizes LangGraph to create a 10-node StateGraph routing architecture. The query flows through an Intent Classifier, Goal Analyzer, Task Decomposer (which builds topological subtask dependency maps), Parallel Executor, Result Fusion, Self-Reflection Check, and a grounding Verification node."
            },
            {
                "title": "Model Context Protocol & plugins registry",
                "content": "The agent interacts with the OS via dynamic plugins registering local Python scripts (like git_mcp and terminal_mcp) and connection managers spawning standard daemon subprocesses (Filesystem MCP, GitHub API MCP, and Playwright Browser MCP) exchanging stdio JSON-RPC payloads."
            }
        ]

        quiz = [
            {
                "question": "Which space element corresponds to a FILE in RepoVerse AI?",
                "options": ["Galaxy", "Star", "Planet", "Moon"],
                "answer": "Planet"
            },
            {
                "question": "What is the primary node orchestration engine in RepoVerse?",
                "options": ["LangChain RAG", "LangGraph StateGraph", "Uvicorn REST APIs", "React flow canvases"],
                "answer": "LangGraph StateGraph"
            },
            {
                "question": "How do official MCP servers connect to our agent?",
                "options": ["Via database schemas", "Spawning daemon subprocesses communicating via stdio streams", "Direct HTTP polling", "Third-party cloud gateways"],
                "answer": "Spawning daemon subprocesses communicating via stdio streams"
            }
        ]

        return {
            "lessons": lessons,
            "quiz": quiz
        }

skill_registry.register("learning", LearningModeSkill())
