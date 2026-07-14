import subprocess
import time
from typing import List, Dict, Any
from backend.mcp.interfaces import IMCPServer
from backend.agent.capabilities import Capability
from backend.agent.permissions import PermissionType
from backend.agent.tool_models import ToolResult

class GitMCPServer(IMCPServer):
    """
    Local MCP Server implementing Git operations via subprocess command line.
    """
    def __init__(self):
        self.name = "git_mcp"
        self._is_active = False

    def initialize(self) -> bool:
        self._is_active = True
        return True

    def discover_capabilities(self) -> List[Capability]:
        return [
            Capability(
                name="git_status",
                description="Gets the repository working status (git status)",
                input_schema={},
                permissions=[PermissionType.READ]
            ),
            Capability(
                name="git_log",
                description="Retrieves commit history (git log)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 5}
                    }
                },
                permissions=[PermissionType.READ]
            ),
            Capability(
                name="git_diff",
                description="Retrieves code modifications diff (git diff)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Optional file path target"}
                    }
                },
                permissions=[PermissionType.READ]
            ),
            Capability(
                name="git_blame",
                description="Runs git blame on a specific file path",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File path target"}
                    },
                    "required": ["file_path"]
                },
                permissions=[PermissionType.READ]
            )
        ]

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy"}

    def _run_git_command(self, args: List[str]) -> str:
        try:
            res = subprocess.run(
                ["git"] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            return f"Git error executing command git {' '.join(args)}: {e.stderr.strip()}"
        except Exception as e:
            return f"Error executing command: {e}"

    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        
        if capability == "git_status":
            result = self._run_git_command(["status"])
        elif capability == "git_log":
            limit = args.get("limit", 5)
            result = self._run_git_command(["log", f"-n", str(limit), "--oneline"])
        elif capability == "git_diff":
            file_path = args.get("file_path")
            cmd = ["diff"]
            if file_path:
                cmd.append(file_path)
            result = self._run_git_command(cmd)
        elif capability == "git_blame":
            file_path = args.get("file_path")
            if not file_path:
                return ToolResult(
                    tool_name=self.name,
                    capability=capability,
                    status="error",
                    latency_ms=0.0,
                    errors=["Missing required file_path parameter."]
                )
            result = self._run_git_command(["blame", file_path])
        else:
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="capability_missing",
                latency_ms=0.0,
                errors=[f"Capability '{capability}' is missing in GitMCPServer."]
            )

        latency = (time.perf_counter() - start_time) * 1000.0
        return ToolResult(
            tool_name=self.name,
            capability=capability,
            status="success" if "Git error" not in result else "error",
            latency_ms=latency,
            result=result,
            errors=[result] if "Git error" in result else None
        )

    def shutdown(self) -> bool:
        self._is_active = False
        return True
