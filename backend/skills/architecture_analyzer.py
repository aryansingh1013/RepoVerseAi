from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry

class ArchitectureAnalyzerSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Architecture Analyzer"

    @property
    def description(self) -> str:
        return "Generates system architecture layer descriptions and Mermaid structural diagrams."

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
        description = "The application implements a decoupled Frontend-Backend pattern: React-Vite handles interactive timeline UI blocks, while a FastAPI server coordinates cognitive planning, AST parsing, and ChromaDB vector queries."

        layers = [
            {"name": "Frontend View Layer", "description": "Vite + TailwindCSS + Lucide Icons rendering files trees, chat consoles, and connection pings."},
            {"name": "REST & WebSocket Layer", "description": "FastAPI uvicorn gateway routing requests, handling configuration updates, and streaming tokens over WebSockets."},
            {"name": "Orchestration & Reasoning Layer", "description": "LangGraph state machine implementing Topological planners, Executors, and Grounding verification checkpoints."},
            {"name": "Plugin / MCP Connection Layer", "description": "Stdio Connection Manager lifecycle-managing subprocess servers (Filesystem, Playwright, Git, Terminal)."},
            {"name": "Database & Parsing Layer", "description": "ChromaDB vector embedding store and AST chunker extractors profiling code hierarchy."}
        ]

        diagram = """graph TD
    UI[Frontend UI React] -->|REST/WebSockets| API[FastAPI Server Gateway]
    API -->|invoke| Graph[LangGraph State Machine]
    Graph -->|Planner Node| Planner[Goal & Task Decomposer]
    Planner -->|Execute| Exec[Parallel Executor Pool]
    Exec -->|MCP Call| Manager[MCP Subprocess Manager]
    Manager -->|stdio jsonrpc| FS[Filesystem MCP]
    Manager -->|stdio jsonrpc| Play[Browser Playwright MCP]
    Manager -->|Python wrapper| Git[Git MCP]
    Manager -->|Python wrapper| Term[Secure Terminal MCP]
    API -->|queries| DB[(ChromaDB Vector Store)]
"""

        return {
            "description": description,
            "layers": layers,
            "diagram": diagram
        }

skill_registry.register("architecture", ArchitectureAnalyzerSkill())
