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
                description=(
                    "Executes an allowlisted, parameter-safe workspace command (pytest, npm run build/lint/test, "
                    "npx tsc --noEmit). Requires terminal_enabled in MCP settings; arbitrary commands and shell "
                    "operators are rejected."
                ),
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
        (Defense in depth only — real enforcement is the argv allowlist in
        validate_terminal_command + shell=False execution.)
        """
        cmd_clean = command.strip().lower()
        destructive_patterns = [
            r"\brm\b", r"\bdel\b", 
            r"\bgit\s+reset\s+--hard\b", r"\bgit\s+push\b", 
            r"\bnpm\s+uninstall\b", r"\bpip\s+uninstall\b",
            r"\bformat\b", r"\brd\b", r"\bmkfs\b", r"\bdd\b",
            r"\bshutdown\b", r"\breboot\b", r"\b(sudo|runas)\b",
            r"\b(chmod|chown)\b", r"\b(curl|wget)\b", r"\bnc\b",
            r"\bssh\b", r"\bscp\b", r"\bbase64\b",
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

        # Gate 0: whole server is opt-in. Command execution is disabled unless
        # explicitly enabled in mcp_settings.json (Settings → MCP Config) — the
        # safe default for any deployed instance.
        if not mcp_settings.get("terminal_enabled", False):
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="permission_denied",
                latency_ms=0.0,
                result="[DISABLED] Terminal execution is off by default. An operator must set "
                       "\"terminal_enabled\": true in backend/mcp_settings.json to turn it on.",
                errors=["TerminalMCPServer disabled by default policy."]
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

        # Gate 1: argv-level allowlist (shell operators impossible; shell=False exec).
        from backend.core.security import validate_terminal_command
        argv, validation_error = validate_terminal_command(command)
        if validation_error:
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="requires_confirmation",
                latency_ms=0.0,
                result=f"[BLOCKED] {validation_error}",
                errors=[validation_error],
            )

        # Gate 2: legacy pattern blocklist as defense in depth.
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

        # Run command with timeout limit — argv form, no shell.
        try:
            timeout_limit = mcp_settings.get("connection_timeout", 10)
            workspace_root = mcp_settings.get("filesystem_root", None)
            res = subprocess.run(
                argv,
                cwd=workspace_root or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
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
