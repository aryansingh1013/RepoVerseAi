import subprocess
import time
import re
from typing import List, Dict, Any
from backend.mcp.interfaces import IMCPServer
from backend.agent.capabilities import Capability
from backend.agent.permissions import PermissionType
from backend.agent.tool_models import ToolResult
from backend.mcp.config import mcp_settings

class TerminalMCPServer(IMCPServer):
    """
    Secure Local Terminal execution server enforcing permission check gates.
    """
    def __init__(self):
        self.name = "terminal_mcp"
        self._is_active = False

    def initialize(self) -> bool:
        self._is_active = True
        return True

    def discover_capabilities(self) -> List[Capability]:
        return [
            Capability(
                name="terminal_execute",
                description="Executes a shell command on the workspace terminal host securely",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The command string to execute"}
                    },
                    "required": ["command"]
                },
                permissions=[PermissionType.WRITE]
            )
        ]

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy"}

    def _is_destructive(self, command: str) -> bool:
        """
        Inspects command string against dangerous patterns.
        """
        cmd_clean = command.strip().lower()
        destructive_patterns = [
            r"\brm\b", r"\bdel\b", 
            r"\bgit\s+reset\s+--hard\b", r"\bgit\s+push\b", 
            r"\bnpm\s+uninstall\b", r"\bpip\s+uninstall\b",
            r"\bformat\b", r"\brd\b"
        ]
        return any(re.search(pattern, cmd_clean) for pattern in destructive_patterns)

    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        
        if capability != "terminal_execute":
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="capability_missing",
                latency_ms=0.0,
                errors=[f"Capability '{capability}' is missing in TerminalMCPServer."]
            )

        command = args.get("command", "")
        if not command:
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="error",
                latency_ms=0.0,
                errors=["Command string is empty."]
            )

        # Safety filters check
        safe_mode = mcp_settings.get("terminal_safe_mode", True)
        if safe_mode and self._is_destructive(command):
            latency = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="requires_confirmation",
                latency_ms=latency,
                result="[BLOCKED] Command execution requires user confirmation under active terminal safeguards.",
                errors=[f"Blocked dangerous execution of command: '{command}'"]
            )

        # Run command with timeout limit
        try:
            timeout_limit = mcp_settings.get("connection_timeout", 10)
            # Run command securely in shell subprocess
            res = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_limit
            )
            
            output = res.stdout.strip()
            err_output = res.stderr.strip()
            
            latency = (time.perf_counter() - start_time) * 1000.0
            
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="success" if res.returncode == 0 else "error",
                latency_ms=latency,
                result=output if res.returncode == 0 else f"Execution failed: {err_output}",
                errors=[err_output] if res.returncode != 0 and err_output else None
            )
        except subprocess.TimeoutExpired:
            latency = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="timeout",
                latency_ms=latency,
                errors=[f"Command execution timed out after {timeout_limit} seconds."]
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="error",
                latency_ms=latency,
                errors=[f"Failed to execute command: {e}"]
            )

    def shutdown(self) -> bool:
        self._is_active = False
        return True
