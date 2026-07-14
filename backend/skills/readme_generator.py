from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry

class ReadmeGeneratorSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "README Generator"

    @property
    def description(self) -> str:
        return "Generates standard professional production manuals and setups docs for the workspace."

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
        markdown = """# RepoVerse AI - Developer Space Station

Welcome to RepoVerse AI, an intelligent agentic workspace platform. RepoVerse combines AST parsers, vector indexes, dynamic subprocess connections, and parallel LangGraph node execution streams into a single workspace panel.

## 🚀 Setup & Startup Manual

### 1. Backend API Host Startup
Verify Python 3.10+ is active.
```bash
pip install -r requirements.txt
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend React Panel Development
Install Node npm nodes dependencies.
```bash
cd frontend
npm install
npm run dev
```

## 🌌 System Architecture Map

```
React Views App (Vite)
  └── REST / WebSockets Connection
       └── FastAPI Backend Gateway
            └── LangGraph Planners & Sorters
                 └── Parallel Executor
                      └── Local Git / Terminal MCP
```

## 🩺 Active Capabilities
*   **AST Code Parser**: Recursively walks folders to identify symbols.
*   **Cognitive Flow Engine**: 10-node StateGraph resolves compound engineering goals.
*   **Model Context Protocol**: Connects Filesystem, GitHub, Git, and Browser subprocesses.
"""

        return {
            "markdown": markdown
        }

skill_registry.register("readme", ReadmeGeneratorSkill())
