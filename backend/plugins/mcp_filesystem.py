import os
import time
from typing import List, Dict, Any
from backend.mcp.manager import MCPSubprocessServer
from backend.mcp.config import mcp_settings
from backend.agent.capabilities import Capability
from backend.agent.permissions import PermissionType
from backend.agent.tool_models import ToolResult

class FilesystemMCPServer(MCPSubprocessServer):
    """
    Subprocess wrapper for the official @modelcontextprotocol/server-filesystem npm package.
    Falls back to a native Python implementation if npx is missing, timed out, or fails.
    """
    def __init__(self):
        # Retrieve the workspace directory from settings
        root_path = mcp_settings.get("filesystem_root")
        if not root_path:
            root_path = os.environ.get("WORKSPACE_DIR", "c:\\Users\\Aryan Singh\\OneDrive\\Desktop\\SUMMERTRAININGPROJECT")
            
        self.root_path = os.path.abspath(root_path)
        self.use_native = False
        command = ["npx", "-y", "@modelcontextprotocol/server-filesystem", self.root_path]
        
        super().__init__(
            name="filesystem_mcp",
            command=command,
            env=None,
            timeout=mcp_settings.get("connection_timeout", 30)
        )

    def initialize(self) -> bool:
        # Try subprocess start first
        success = super().initialize()
        if not success:
            print("FilesystemMCPServer: Subprocess initialization failed. Falling back to native Python mode.")
            self.use_native = True
            self._is_active = True
            return True
        return True

    def discover_capabilities(self) -> List[Capability]:
        if self.use_native:
            return [
                Capability(
                    name="filesystem_list",
                    description="List files in the workspace directory.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "relative_path": {"type": "string", "default": "."}
                        }
                    },
                    permissions=[PermissionType.READ]
                ),
                Capability(
                    name="filesystem_read",
                    description="Read the contents of a file inside the workspace.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "relative_path": {"type": "string"},
                            "start_line": {"type": "integer", "default": 1},
                            "end_line": {"type": "integer", "default": 100}
                        },
                        "required": ["relative_path"]
                    },
                    permissions=[PermissionType.READ]
                )
            ]
        return super().discover_capabilities()

    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        if self.use_native:
            start_time = time.perf_counter()
            try:
                if capability == "filesystem_list":
                    rel_path = args.get("relative_path", ".")
                    full_path = self._resolve_path(rel_path)
                    items = os.listdir(full_path)
                    result = [f"{'[DIR]' if os.path.isdir(os.path.join(full_path, item)) else '[FILE]'} {item}" for item in items]
                    res_str = "\n".join(result) if result else "Directory is empty."
                    return ToolResult(
                        tool_name=self.name,
                        capability=capability,
                        status="success",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                        result=res_str
                    )
                elif capability == "filesystem_read":
                    rel_path = args.get("relative_path", "")
                    if not rel_path:
                        return ToolResult(
                            tool_name=self.name,
                            capability=capability,
                            status="success",
                            latency_ms=(time.perf_counter() - start_time) * 1000.0,
                            result="No relative_path provided. Skipped file read."
                        )
                    
                    full_path = self._resolve_path(rel_path)
                    if os.path.isdir(full_path):
                        return ToolResult(
                            tool_name=self.name,
                            capability=capability,
                            status="success",
                            latency_ms=(time.perf_counter() - start_time) * 1000.0,
                            result=f"Path '{rel_path}' is a directory. Use filesystem_list to view its contents."
                        )
                    
                    start_line = args.get("start_line", 1)
                    end_line = args.get("end_line", 100)
                    
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    
                    start = max(0, start_line - 1)
                    end = min(len(lines), end_line)
                    output = [f"{idx+1}: {lines[idx].rstrip()}" for idx in range(start, end)]
                    res_str = "\n".join(output) if output else "No content in specified line range."
                    return ToolResult(
                        tool_name=self.name,
                        capability=capability,
                        status="success",
                        latency_ms=(time.perf_counter() - start_time) * 1000.0,
                        result=res_str
                    )
            except Exception as e:
                return ToolResult(
                    tool_name=self.name,
                    capability=capability,
                    status="error",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    errors=[str(e)]
                )
        return super().execute(capability, args)

    def _resolve_path(self, path: str) -> str:
        resolved = os.path.abspath(os.path.join(self.root_path, path))
        if not resolved.startswith(self.root_path):
            raise PermissionError("Access outside workspace is restricted.")
        return resolved
