from typing import List, Dict, Any
import time
from backend.mcp.interfaces import IMCPServer
from backend.agent.capabilities import Capability
from backend.agent.permissions import PermissionType
from backend.agent.tool_models import ToolResult

class MockMCPServer(IMCPServer):
    """
    Mock MCP Server to test dynamic capability discovery and execution pipeline.
    """
    def __init__(self):
        self.name = "mock_server"
        self._is_active = False

    def initialize(self) -> bool:
        self._is_active = True
        print("MockMCPServer: Initialized successfully.")
        return True

    def discover_capabilities(self) -> List[Capability]:
        return [
            Capability(
                name="mock_read_file",
                description="Mock capability to simulate reading files.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative file path"}
                    },
                    "required": ["path"]
                },
                permissions=[PermissionType.READ]
            ),
            Capability(
                name="mock_git_log",
                description="Mock capability to retrieve git history commits.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 5}
                    }
                },
                permissions=[PermissionType.READ]
            )
        ]

    def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "uptime_seconds": 120,
            "mock_telemetry": "active"
        }

    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        
        if not self._is_active:
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="error",
                latency_ms=0.0,
                errors=["Mock server is offline."]
            )

        latency = (time.perf_counter() - start_time) * 1000.0
        
        if capability == "mock_read_file":
            path = args.get("path", "unknown")
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="success",
                latency_ms=latency,
                result=f"[MOCK FILE CONTENT] Mock content of file '{path}'"
            )
        elif capability == "mock_git_log":
            limit = args.get("limit", 5)
            commits = [f"Commit {i}: mock git message" for i in range(limit)]
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="success",
                latency_ms=latency,
                result="\n".join(commits)
            )
        else:
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="capability_missing",
                latency_ms=latency,
                errors=[f"Capability '{capability}' is missing in MockMCPServer."]
            )

    def shutdown(self) -> bool:
        self._is_active = False
        print("MockMCPServer: Shut down.")
        return True
