import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.core.config import settings
from backend.core.theme import THEME_CONFIG
from backend.parser.galaxy_parser import GalaxyParser
from backend.parser.chunk_builder import ChunkBuilder
from backend.rag.vector_store import VectorStore
from backend.rag.retriever import HybridRetriever
from backend.agent.nodes import AgentNodes
from backend.agent.graph import create_agent_graph
from backend.mcp.registry import MCPServerRegistry
from backend.mcp.loader import DynamicToolLoader
from backend.agent.registry import AgentToolRegistry

app = FastAPI(title="RepoVerse AI Backend", version="1.0.0")

# Enable CORS for the frontend (Vite defaults to port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances — wrapped in try/except so startup errors don't prevent port binding
try:
    parser = GalaxyParser()
    vector_store = VectorStore()
    retriever = HybridRetriever(vector_store)
    chunk_builder = ChunkBuilder()
except Exception as _e:
    print(f"WARNING: Core components failed to init: {_e}")
    parser = None
    vector_store = None
    retriever = None
    chunk_builder = None

try:
    mcp_registry = MCPServerRegistry()
    tool_loader = DynamicToolLoader(mcp_registry)
    tool_loader.load_plugins()
    from backend.mcp.connection_manager import MCPConnectionManager
    mcp_manager = MCPConnectionManager(mcp_registry)
    mcp_manager.reload_connections()
    agent_tool_registry = AgentToolRegistry(mcp_registry)
except Exception as _e:
    print(f"WARNING: MCP/Agent components failed to init: {_e}")
    mcp_registry = None
    tool_loader = None
    mcp_manager = None
    agent_tool_registry = None

try:
    agent_nodes = AgentNodes(retriever, settings.WORKSPACE_DIR, agent_tool_registry)
    agent_graph = create_agent_graph(agent_nodes)
except Exception as _e:
    print(f"WARNING: Agent graph failed to init: {_e}")
    agent_nodes = None
    agent_graph = None

# In-memory store for repository summaries and chunks (for BM25 fit)
indexed_data = {
    "summary": None,
    "chunks": []
}

# Request schema for updating settings
class SettingsUpdate(BaseModel):
    ollama_endpoint: Optional[str] = None
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    fallback_order: Optional[List[str]] = None
    rotation_strategy: Optional[str] = None
    fallback_llm: Optional[str] = None
    embedding_model: Optional[str] = None

# Request schema for cloning remote git repositories
class CloneRequest(BaseModel):
    repo_url: str

@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "RepoVerse AI Backend is healthy"}

@app.get("/api/theme")
def get_theme():
    return THEME_CONFIG

@app.get("/api/scan")
def scan_galaxy():
    """Scans the codebase tree structure."""
    try:
        tree = parser.scan_directory()
        return tree
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/index")
async def index_galaxy():
    """Indexes the active codebase (Galaxy) into ChromaDB and BM25."""
    # Allowed source-code extensions only (skip binaries, images, lock files)
    ALLOWED_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md",
        ".yaml", ".yml", ".toml", ".txt", ".html", ".css",
        ".prisma", ".sql", ".sh", ".env.example", ".graphql",
        ".go", ".rs", ".java", ".c", ".cpp", ".h"
    }
    MAX_FILE_BYTES = 150_000  # Skip files larger than 150KB (binary/generated)
    EXCLUDE_DIRS = {
        ".git", "__pycache__", "node_modules", ".gemini",
        "venv", ".venv", "db", "dist", "build", ".agents",
        ".vscode", ".idea", ".next", ".turbo"
    }
    EXCLUDE_FILES = {
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        ".gitignore", ".env", "tsconfig.tsbuildinfo"
    }

    def sync_index():
        workspace = settings.WORKSPACE_DIR

        # 1. Fast direct walk – collect file paths without re-reading files
        file_paths = []
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                _, ext = os.path.splitext(file)
                if ext.lower() not in ALLOWED_EXTENSIONS:
                    continue
                full = os.path.join(root, file)
                try:
                    if os.path.getsize(full) > MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                file_paths.append(full)

        # 2. Build chunks using the singleton builder
        all_chunks = []
        for file_path in file_paths:
            chunks = chunk_builder.build_chunks(file_path, workspace)
            all_chunks.extend(chunks)

        # 3. Check if collection already has chunks and we can skip re-embedding
        count = vector_store.collection.count()
        use_cache = False
        if count > 0:
            # Check if the cache matches the current workspace
            sample = vector_store.collection.get(limit=1, include=['metadatas'])
            if sample and sample.get('metadatas') and sample['metadatas'][0]:
                sample_path = sample['metadatas'][0].get('path')
                full_sample_path = os.path.join(workspace, sample_path)
                if os.path.exists(full_sample_path):
                    use_cache = True

        if use_cache:
            print(f"VectorStore: Found {count} cached chunks matching workspace. Loading cache.")
            results = vector_store.collection.get(include=['documents', 'metadatas'])
            all_chunks = []
            if results and 'documents' in results:
                docs = results['documents']
                metas = results['metadatas']
                ids = results['ids']
                for idx in range(len(docs)):
                    meta = metas[idx].copy()
                    try:
                        import json
                        meta["imports"] = json.loads(meta["imports"]) if isinstance(meta["imports"], str) else meta["imports"]
                        meta["exports"] = json.loads(meta["exports"]) if isinstance(meta["exports"], str) else meta["exports"]
                    except Exception:
                        pass
                    all_chunks.append({
                        "id": ids[idx],
                        "content": docs[idx],
                        "metadata": meta
                    })
            retriever.fit_bm25(all_chunks)
        else:
            print("VectorStore: No valid cache found. Re-indexing.")
            vector_store.clear()
            if all_chunks:
                vector_store.add_chunks(all_chunks)
                retriever.fit_bm25(all_chunks)
        indexed_data["chunks"] = all_chunks

        # 4. Generate lightweight heuristics summary (no LLM call)
        summary = parser.generate_heuristics_summary()
        indexed_data["summary"] = summary

        return summary, len(all_chunks), len(file_paths)

    try:
        loop = asyncio.get_event_loop()
        summary, num_chunks, num_files = await loop.run_in_executor(None, sync_index)

        return {
            "status": "success",
            "message": f"Successfully indexed {num_chunks} chunks from {num_files} files.",
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary")
def get_summary():
    """Gets the precompiled repository summary. Generates heuristic summary if not indexed."""
    if not indexed_data["summary"]:
        indexed_data["summary"] = parser.generate_heuristics_summary()
    return indexed_data["summary"]

@app.get("/api/file")
def get_file_content(path: str = Query(..., description="Relative path of file to preview")):
    try:
        full_path = os.path.join(settings.WORKSPACE_DIR, path)
        # Security check: resolve and verify inside workspace
        resolved_path = os.path.abspath(full_path)
        if not resolved_path.startswith(os.path.abspath(settings.WORKSPACE_DIR)):
            raise HTTPException(status_code=403, detail="Access outside workspace is forbidden.")
            
        if not os.path.exists(resolved_path):
            raise HTTPException(status_code=404, detail="File not found.")
            
        with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        from backend.parser.code_analyzer import CodeAnalyzer
        analysis = CodeAnalyzer.analyze(content, path)
            
        return {
            "path": path,
            "content": content,
            "language": analysis.get("language", "text"),
            "symbols": analysis.get("symbols", []),
            "imports": analysis.get("imports", []),
            "exports": analysis.get("exports", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def set_active_workspace(target_path: str):
    target_path = os.path.abspath(target_path)
    settings.WORKSPACE_DIR = target_path
    if parser:
        parser.root_dir = target_path
    if agent_nodes:
        agent_nodes.workspace_dir = target_path
        if hasattr(agent_nodes, "tools") and agent_nodes.tools:
            agent_nodes.tools.workspace_dir = target_path
    
    if mcp_registry:
        fs_tool = mcp_registry.get_tool("filesystem_mcp")
        if fs_tool:
            fs_tool.root_path = target_path
            if hasattr(fs_tool, "command"):
                fs_tool.command = ["npx", "-y", "@modelcontextprotocol/server-filesystem", target_path]

    # Persist active workspace path to JSON
    try:
        conf_dir = os.path.join(os.path.dirname(__file__), "core")
        os.makedirs(conf_dir, exist_ok=True)
        conf_path = os.path.join(conf_dir, "active_workspace.json")
        import json
        with open(conf_path, "w", encoding="utf-8") as f:
            json.dump({"active_workspace": target_path}, f, indent=2)
        print(f"Workspace persisted successfully: {target_path}")
    except Exception as e:
        print(f"Failed to persist workspace setting: {e}")

# Background state manager for workspace switching/cloning
workspace_status = {
    "status": "ready",  # ready, cloning, indexing, error
    "repo_name": "",
    "error_message": "",
    "current_path": settings.WORKSPACE_DIR
}

class SelectWorkspaceRequest(BaseModel):
    path: str

async def bg_clone_and_index(url: str):
    global workspace_status
    workspace_status["status"] = "cloning"
    workspace_status["error_message"] = ""
    
    try:
        import subprocess
        import shutil
        
        repo_name = url.split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        workspace_status["repo_name"] = repo_name
        
        cloned_repos_dir = os.path.join(settings.DB_DIR, "cloned_repos")
        os.makedirs(cloned_repos_dir, exist_ok=True)
        local_path = os.path.join(cloned_repos_dir, repo_name)
        
        # Clone repository
        if os.path.exists(local_path):
            try:
                subprocess.run(
                    ["git", "pull"],
                    cwd=local_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=30
                )
            except Exception:
                shutil.rmtree(local_path, ignore_errors=True)
                subprocess.run(
                    ["git", "clone", url, local_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=120
                )
        else:
            subprocess.run(
                ["git", "clone", url, local_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=120
            )
            
        workspace_status["status"] = "indexing"
        target_path = os.path.abspath(local_path)
        
        set_active_workspace(target_path)
                
        # Trigger index
        await index_galaxy()
        
        workspace_status["status"] = "ready"
        workspace_status["current_path"] = target_path
        
    except Exception as e:
        workspace_status["status"] = "error"
        workspace_status["error_message"] = str(e)

async def bg_select_and_index(target_path: str):
    global workspace_status
    workspace_status["status"] = "indexing"
    workspace_status["error_message"] = ""
    workspace_status["repo_name"] = os.path.basename(target_path)
    
    try:
        set_active_workspace(target_path)
                
        await index_galaxy()
        workspace_status["status"] = "ready"
        workspace_status["current_path"] = target_path
    except Exception as e:
        workspace_status["status"] = "error"
        workspace_status["error_message"] = str(e)

@app.get("/api/workspace/status")
def get_workspace_status():
    """Returns the current background task status of the workspace switcher/cloner."""
    global workspace_status
    workspace_status["current_path"] = settings.WORKSPACE_DIR
    return workspace_status

@app.get("/api/workspace/browse")
def browse_directory():
    """Opens a native OS folder dialog using Tkinter in a separate thread."""
    import queue
    import threading
    import tkinter as tk
    from tkinter import filedialog
    
    result_queue = queue.Queue()
    
    def run_dialog():
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            directory = filedialog.askdirectory(title="Select Local Workspace Directory")
            root.destroy()
            result_queue.put(directory)
        except Exception as e:
            result_queue.put(e)
            
    thread = threading.Thread(target=run_dialog)
    thread.start()
    thread.join()
    
    res = result_queue.get()
    if isinstance(res, Exception):
        import traceback
        traceback.print_exception(type(res), res, res.__traceback__)
        raise HTTPException(status_code=500, detail=f"Tkinter error: {type(res).__name__}: {str(res)}")
        
    if res:
        return {"status": "success", "path": os.path.abspath(res)}
    return {"status": "cancelled", "path": None}

@app.get("/api/workspace/list_directories")
def list_directories(path: Optional[str] = None):
    """Lists subdirectories of a given path for the web-based folder selector."""
    try:
        if not path:
            # Default to current workspace directory or user home
            path = settings.WORKSPACE_DIR or os.path.expanduser("~")
            
        path = os.path.abspath(path)
        
        # Check that path exists, fallback to home directory if not
        if not os.path.exists(path):
            path = os.path.expanduser("~")
            
        subdirs = []
        for name in os.listdir(path):
            full_path = os.path.join(path, name)
            try:
                if os.path.isdir(full_path):
                    # Skip system/hidden folders to keep it clean
                    if name.startswith(".") or name in {"node_modules", "$RECYCLE.BIN", "System Volume Information"}:
                        continue
                    subdirs.append(name)
            except OSError:
                continue
                
        subdirs.sort(key=str.lower)
        
        parent_path = os.path.dirname(path)
        if parent_path == path:
            parent_path = None
            
        return {
            "status": "success",
            "current_path": path,
            "parent_path": parent_path,
            "subdirectories": subdirs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/select")
def select_workspace(payload: SelectWorkspaceRequest, background_tasks: BackgroundTasks):
    """Triggers background workspace switcher indexing for a local folder path."""
    target_path = os.path.abspath(payload.path.strip())
    if not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail="Directory path does not exist.")
        
    background_tasks.add_task(bg_select_and_index, target_path)
    return {"status": "success", "message": "Indexing started in background."}

@app.post("/api/clone")
def clone_repository(payload: CloneRequest, background_tasks: BackgroundTasks):
    """Triggers background clone and index operation."""
    url = payload.repo_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Repository URL is required.")
        
    background_tasks.add_task(bg_clone_and_index, url)
    return {"status": "success", "message": "Cloning started in background."}

@app.post("/api/settings")
def update_settings(payload: SettingsUpdate):
    """Dynamically updates model router configurations without credentials input."""
    import yaml
    
    if payload.fallback_llm is not None:
        settings.FALLBACK_LLM = payload.fallback_llm
    if payload.embedding_model is not None:
        settings.EMBEDDING_MODEL = payload.embedding_model

    # Update Model Router configs dynamically
    from backend.llm.model_router import model_router
    from backend.llm.task_router import task_router
    from backend.llm.models.provider_registry import provider_registry

    if payload.ollama_endpoint is not None:
        provider_registry.ollama_endpoint = payload.ollama_endpoint

    if payload.rotation_strategy is not None:
        for prov in provider_registry.rotation_strategy.keys():
            provider_registry.rotation_strategy[prov] = payload.rotation_strategy

    if payload.fallback_order is not None:
        model_router.fallback_order = payload.fallback_order

    if payload.preferred_provider is not None and payload.preferred_model is not None:
        task_router.rules["chat"] = (payload.preferred_provider, payload.preferred_model)

    # Persist configs to disk (credentials are backend-only in .env)
    try:
        model_conf_data = {
            "tasks": {task: {"provider": prov, "model": m} for task, (prov, m) in task_router.rules.items()}
        }
        with open(task_router.config_path, "w") as f:
            yaml.safe_dump(model_conf_data, f)

        provider_conf_data = {
            "fallback_order": model_router.fallback_order,
            "providers": {
                prov: {
                    "preferred_key_selection": provider_registry.rotation_strategy.get(prov, "round_robin")
                } for prov in ["groq", "openai", "gemini", "openrouter"]
            }
        }
        provider_conf_data["providers"]["ollama"] = {
            "endpoint": provider_registry.ollama_endpoint
        }
        with open(model_router.provider_config_path, "w") as f:
            yaml.safe_dump(provider_conf_data, f)
    except Exception as ex:
        print(f"Error saving config files: {ex}")

    # Reinitialize LLM client in nodes
    global agent_nodes, agent_graph
    agent_nodes._init_llm_client()
    agent_graph = create_agent_graph(agent_nodes)

    return {
        "status": "success",
        "message": "Settings updated and persisted successfully.",
        "active_model": agent_nodes.model_name
    }

@app.get("/api/llm/telemetry")
def get_llm_telemetry():
    """Returns active telemetry logs from the model router."""
    from backend.llm.model_router import model_router
    from backend.llm.models.provider_registry import provider_registry
    from backend.llm.models.model_registry import MODEL_REGISTRY
    
    key_usage_stats = {}
    for prov, keys in provider_registry.keys.items():
        key_usage_stats[prov] = [
            {
                "alias": k.alias,
                "success_count": k.success_count,
                "failure_count": k.failure_count,
                "rate_limit_count": k.rate_limit_count,
                "is_healthy": k.is_healthy
            } for k in keys
        ]

    avg_latency = 0.0
    if model_router.telemetry["latency_count"] > 0:
        avg_latency = model_router.telemetry["latency_sum"] / model_router.telemetry["latency_count"]

    available_providers = ["groq", "openai", "huggingface", "gemini", "openrouter", "ollama"]
    connected_models = list(MODEL_REGISTRY.keys())

    return {
        "requests_total": model_router.telemetry["requests_total"],
        "failures_total": model_router.telemetry["failures_total"],
        "rate_limits_total": model_router.telemetry["rate_limits_total"],
        "fallback_events_total": model_router.telemetry["fallback_events_total"],
        "latency_average_ms": avg_latency * 1000.0,
        "fallback_chain_log": model_router.telemetry["fallback_chain_log"][-20:],
        "key_usage": key_usage_stats,
        "available_providers": available_providers,
        "connected_models": connected_models,
        "active_provider": model_router.fallback_order[0] if model_router.fallback_order else "groq",
        "active_model": agent_nodes.model_name
    }

class MCPSettingsPayload(BaseModel):
    filesystem_root: Optional[str] = None
    terminal_safe_mode: Optional[bool] = None
    connection_timeout: Optional[int] = None
    refresh_interval: Optional[int] = None

@app.post("/api/mcp/config")
def save_mcp_config(payload: MCPSettingsPayload):
    from backend.mcp.config import mcp_settings
    update_dict = {k: v for k, v in payload.model_dump().items() if v is not None}
    mcp_settings.save(update_dict)
    mcp_manager.reload_connections()
    return {"status": "success", "settings": get_mcp_config()}

@app.get("/api/mcp/config")
def get_mcp_config():
    from backend.mcp.config import mcp_settings
    res = dict(mcp_settings.settings)
    res.pop("github_token", None)
    return res

@app.get("/api/mcp/dashboard")
def get_mcp_dashboard_status():
    return mcp_manager.get_status_telemetry()

# Skills APIs (Phase 5)
import backend.skills

@app.get("/api/skills")
def get_skills_list():
    from backend.skills.registry import skill_registry
    return skill_registry.list_skills()

@app.post("/api/skills/execute/{slug}")
def execute_skill(slug: str):
    from backend.skills.skill_manager import skill_manager
    try:
        res = skill_manager.run_skill(slug, f"Analyze {slug}", agent_graph, settings.WORKSPACE_DIR)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ExportPayload(BaseModel):
    result: Dict[str, Any]

@app.post("/api/skills/export/{slug}")
def export_skill_report(slug: str, payload: ExportPayload):
    from backend.skills.skill_manager import skill_manager
    try:
        report = skill_manager.export_report(slug, payload.result)
        return {"markdown": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive text query from client
            query = await websocket.receive_text()
            
            # Initial state
            state = {
                "query": query,
                "messages": [],
                "needs_retrieval": False,
                "needs_tool": False,
                "is_verified": False,
                "out_of_context": False,
                "retrieved_contexts": [],
                "capability_requests": [],
                "tool_outputs": [],
                "agent_steps": [],
                "response": "",
                "citations": [],
                "confidence_score": 0.0,
                "retries": 0,
                "reasoning_trace": [],
                "goal_metadata": {},
                "tasks_metadata": [],
                "reflection_status": {}
            }

            # Run LangGraph node execution step-by-step
            # We can stream execution logs back to client dynamically!
            steps_sent = 0
            
            # Run graph in thread pool as it performs blocking I/O (network, file reads, embeddings)
            loop = asyncio.get_event_loop()
            
            # Perform run inside event loop executor
            def run_graph():
                return agent_graph.invoke(state)

            final_state = await loop.run_in_executor(None, run_graph)

            # Stream steps
            agent_steps = final_state.get("agent_steps", [])
            for step in agent_steps:
                await websocket.send_json({
                    "type": "step",
                    "content": step
                })
                await asyncio.sleep(0.3) # subtle delay to make steps readable

            # Send final response and metadata
            await websocket.send_json({
                "type": "response",
                "content": final_state.get("response", "")
            })
            
            await websocket.send_json({
                "type": "citations",
                "content": final_state.get("citations", [])
            })
            
            await websocket.send_json({
                "type": "confidence",
                "content": final_state.get("confidence_score", 0.0)
            })

            # Send Cognitive Timeline Metadata (Phase 3)
            await websocket.send_json({
                "type": "goal_metadata",
                "content": final_state.get("goal_metadata", {})
            })
            await websocket.send_json({
                "type": "tasks_metadata",
                "content": final_state.get("tasks_metadata", [])
            })
            await websocket.send_json({
                "type": "reasoning_trace",
                "content": final_state.get("reasoning_trace", [])
            })
            await websocket.send_json({
                "type": "reflection_status",
                "content": final_state.get("reflection_status", {})
            })

            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        print("Chat WebSocket client disconnected.")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass

# ── Serve built React frontend (for HF Spaces / production single-container) ──
import pathlib
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_frontend_dist = pathlib.Path(__file__).parent.parent / "frontend" / "dist"

if _frontend_dist.exists():
    # Mount static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(str(_frontend_dist / "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Catch-all to support React Router client-side routing."""
        # Don't intercept /api/* or /ws/* routes
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        return FileResponse(str(_frontend_dist / "index.html"))

if __name__ == "__main__":
    import uvicorn
    # Use config port & host
    uvicorn.run("backend.app:app", host=settings.HOST, port=settings.PORT, reload=False)

