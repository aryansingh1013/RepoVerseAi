import os
import subprocess
import json
import threading
import time
from typing import Dict, Any, List, Optional
from backend.mcp.interfaces import IMCPServer
from backend.agent.capabilities import Capability
from backend.agent.tool_models import ToolResult

class MCPSubprocessServer(IMCPServer):
    """
    Launches an external MCP server via stdio (command execution)
    and manages JSON-RPC exchanges over stdin/stdout.
    """
    def __init__(self, name: str, command: List[str], env: Optional[Dict[str, str]] = None, timeout: int = 10):
        self.name = name
        self.command = command
        self.env = env
        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self._capabilities: List[Capability] = []
        self._is_active = False
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        try:
            # Prepare environment variables
            run_env = os.environ.copy()
            if self.env:
                run_env.update(self.env)

            # Start subprocess with stdio pipelines
            # On Windows, shell=True is needed to run command batch scripts like 'npx'
            is_windows = os.name == 'nt'
            cmd = list(self.command)
            if is_windows and cmd and cmd[0] == "npx":
                cmd[0] = "npx.cmd"

            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=run_env,
                bufsize=1,
                shell=is_windows
            )
            self._is_active = True
            
            # Perform initial handshake JSON-RPC exchange if standard protocol is required
            # For simplicity, we declare standard capabilities or query them from the server
            self._capabilities = self._query_capabilities_handshake()
            return True
        except Exception as e:
            print(f"SubprocessManager: Failed to start process '{self.name}' with command {self.command}: {e}")
            self._is_active = False
            return False

    def _query_capabilities_handshake(self) -> List[Capability]:
        # Under normal MCP initialization: client sends initialize request, server returns capabilities
        # We can send a mock initialize request to verify handshake:
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "RepoVerseClient", "version": "1.0.0"},
                "capabilities": {}
            }
        }
        
        try:
            res = self._send_json_rpc(init_request)
            if res and "result" in res:
                server_caps = res["result"].get("capabilities", {})
                # Map standard server capability schemas to our Capability class
                caps_list = []
                tools = server_caps.get("tools", [])
                for t in tools:
                    caps_list.append(Capability(
                        name=t.get("name"),
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                        permissions=[] # Derived dynamically or declared
                    ))
                return caps_list
        except Exception as e:
            print(f"SubprocessManager Handshake Error for '{self.name}': {e}")
            
        return []

    def _send_json_rpc(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._is_active or not self.process or not self.process.stdin or not self.process.stdout:
            return None

        with self._lock:
            try:
                # Write request
                raw_req = json.dumps(payload) + "\n"
                self.process.stdin.write(raw_req)
                self.process.stdin.flush()

                # Read response (blocking read with timeout in a separate thread if needed)
                # To be simple and robust: we read line by line
                # Standard Python subprocess readline does not have a timeout, so we use a non-blocking timeout strategy
                # or assume fast stdio execution. Let's do a basic line read:
                raw_res = self.process.stdout.readline()
                if not raw_res:
                    return None
                return json.loads(raw_res.strip())
            except Exception as e:
                print(f"SubprocessManager Communication Error in '{self.name}': {e}")
                return None

    def discover_capabilities(self) -> List[Capability]:
        return self._capabilities

    def health(self) -> Dict[str, Any]:
        if not self._is_active or not self.process:
            return {"status": "unhealthy", "errors": ["Subprocess not active."]}
        
        # Check process status
        poll = self.process.poll()
        if poll is not None:
            self._is_active = False
            return {
                "status": "unhealthy",
                "errors": [f"Subprocess terminated with exit code {poll}."]
            }
            
        return {
            "status": "healthy",
            "uptime_seconds": 100, # Simulated or tracked
            "pid": self.process.pid
        }

    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        start_time = time.perf_counter()
        
        if not self._is_active:
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="error",
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                errors=["MCP server subprocess is not running."]
            )

        # Build JSON-RPC call request
        call_req = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {
                "name": capability,
                "arguments": args
            }
        }

        try:
            res = self._send_json_rpc(call_req)
            latency = (time.perf_counter() - start_time) * 1000.0
            
            if res:
                if "error" in res:
                    return ToolResult(
                        tool_name=self.name,
                        capability=capability,
                        status="error",
                        latency_ms=latency,
                        errors=[res["error"].get("message", "Unknown JSON-RPC error")]
                    )
                else:
                    return ToolResult(
                        tool_name=self.name,
                        capability=capability,
                        status="success",
                        latency_ms=latency,
                        result=res.get("result", {}).get("content", "")
                    )
            else:
                return ToolResult(
                    tool_name=self.name,
                    capability=capability,
                    status="timeout",
                    latency_ms=latency,
                    errors=["No response received from the subprocess standard output stream."]
                )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                tool_name=self.name,
                capability=capability,
                status="error",
                latency_ms=latency,
                errors=[f"Execution exception: {e}"]
            )

    def shutdown(self) -> bool:
        self._is_active = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
                return True
            except Exception:
                try:
                    self.process.kill()
                    return True
                except Exception:
                    pass
        return False
