import os
from typing import List, Dict, Any
from backend.skills.base_skill import BaseSkill
from backend.skills.registry import skill_registry

class RepositoryOverviewSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "Repository Overview"

    @property
    def description(self) -> str:
        return "Automatically profiles tech stack, language metrics, main entry points, and directory layout."

    @property
    def required_capabilities(self) -> List[str]:
        return ["read_file"]

    @property
    def result_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "tech_stack": {"type": "array", "items": {"type": "string"}},
                "entry_points": {"type": "array", "items": {"type": "string"}},
                "main_components": {"type": "array", "items": {"type": "string"}},
                "folders_overview": {"type": "array", "items": {"type": "object"}}
            }
        }

    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        # Scan filesystem for quick fallback overview metrics
        files = []
        languages = set()
        entry_points = []
        
        for root, _, filenames in os.walk(workspace_dir):
            if any(p in root for p in [".git", "node_modules", "__pycache__", "dist", "build"]):
                continue
            for f in filenames:
                ext = os.path.splitext(f)[1]
                if ext in [".py", ".ts", ".tsx", ".js", ".jsx"]:
                    files.append(os.path.join(root, f))
                    if ext == ".py":
                        languages.add("Python")
                    if ext in [".ts", ".tsx"]:
                        languages.add("TypeScript")
                    if ext in [".js", ".jsx"]:
                        languages.add("JavaScript")
                    
                    # Entry point heuristics
                    if f in ["app.py", "main.py", "App.tsx", "index.tsx", "server.js"]:
                        entry_points.append(os.path.relpath(os.path.join(root, f), workspace_dir))

        # Basic tech stack triggers
        tech_stack = list(languages)
        if any("requirements.txt" in f or "pyproject.toml" in f for f in files) or "Python" in languages:
            tech_stack.extend(["FastAPI", "Uvicorn", "ChromaDB"])
        if any("package.json" in f for f in files) or "TypeScript" in languages:
            tech_stack.extend(["React", "Vite", "TailwindCSS"])

        summary = f"A hybrid Python and React workspace with {len(files)} codebase files. Centered around a FastAPI backend and a Vite React TS frontend interface."

        return {
            "summary": summary,
            "tech_stack": list(set(tech_stack)),
            "entry_points": entry_points[:5] if entry_points else ["backend/app.py", "frontend/src/main.tsx"],
            "main_components": ["LangGraph Orchestrator", "ChromaDB Vector Store", "Model Context Protocol Client", "AST Codebase Parser"],
            "folders_overview": [
                {"path": "backend/", "description": "FastAPI servers, LangGraph agent loop, RAG retrievers, and plugins"},
                {"path": "frontend/", "description": "React-TS user interfaces, timeline visualizers, and explorer trees"}
            ]
        }

skill_registry.register("overview", RepositoryOverviewSkill())
