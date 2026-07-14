import time
import os
from typing import Dict, Any, List, Optional
from backend.mcp.manager import MCPSubprocessServer
from backend.mcp.config import mcp_settings
from backend.mcp.registry import MCPServerRegistry

class MCPConnectionManager:
    def __init__(self, registry: MCPServerRegistry):
        self.registry = registry
        self.active_servers: Dict[str, MCPSubprocessServer] = {}
        self.execution_counts: Dict[str, int] = {}
        self.error_logs: Dict[str, List[str]] = {}
        self.connection_times: Dict[str, float] = {}

    def connect_server(self, name: str, command: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Spawns a stdio-based subprocess server, registers it, and executes initial handshake.
        """
        # Shutdown existing if running
        self.disconnect_server(name)

        timeout = mcp_settings.get("connection_timeout", 30)
        server = MCPSubprocessServer(name, command, env=env, timeout=timeout)
        
        start_time = time.perf_counter()
        success = server.initialize()
        latency = (time.perf_counter() - start_time) * 1000.0

        if success:
            self.active_servers[name] = server
            self.execution_counts[name] = 0
            self.error_logs[name] = []
            self.connection_times[name] = time.time()
            # Register in MCPServerRegistry
            self.registry.register(name, server)
            print(f"ConnectionManager: Connected and registered '{name}' (latency: {latency:.1f}ms).")
            return True
        else:
            self.error_logs[name] = [f"Failed to start subprocess command {command}"]
            print(f"ConnectionManager Error: Failed to connect server '{name}'")
            return False

    def disconnect_server(self, name: str):
        if name in self.active_servers:
            server = self.active_servers[name]
            try:
                server.shutdown()
            except Exception as e:
                print(f"ConnectionManager: Error shutting down server '{name}': {e}")
            self.registry.unregister(name)
            del self.active_servers[name]
            print(f"ConnectionManager: Disconnected '{name}'.")

    def increment_execution_count(self, server_name: str):
        if server_name in self.execution_counts:
            self.execution_counts[server_name] += 1

    def log_server_error(self, server_name: str, error: str):
        if server_name not in self.error_logs:
            self.error_logs[server_name] = []
        self.error_logs[server_name].append(error)
        if len(self.error_logs[server_name]) > 50:
            self.error_logs[server_name].pop(0)

    def get_status_telemetry(self) -> List[Dict[str, Any]]:
        """
        Generates structured status log report for frontend dashboard cards.
        """
        telemetry = []
        for name in list(self.active_servers.keys()) + ["mock_server"]:
            # Standard mock handling
            if name == "mock_server":
                tool = self.registry.get_tool("mock_server")
                if tool:
                    health = tool.health()
                    telemetry.append({
                        "name": "mock_server",
                        "status": health.get("status", "healthy"),
                        "latency_ms": 0.1,
                        "capabilities": [c.name for c in tool.discover_capabilities()],
                        "version": "1.0.0 (Mock)",
                        "execution_count": 5,
                        "errors": []
                    })
                continue

            server = self.active_servers[name]
            health = server.health()
            caps = []
            try:
                caps = [c.name for c in server.discover_capabilities()]
            except Exception:
                pass

            telemetry.append({
                "name": name,
                "status": health.get("status", "healthy"),
                "latency_ms": health.get("latency_ms", 1.5),
                "capabilities": caps,
                "version": "1.0.0",
                "execution_count": self.execution_counts.get(name, 0),
                "errors": self.error_logs.get(name, [])
            })
        return telemetry

    def reload_connections(self):
        """
        Reads config files and restarts official servers in real time.
        """
        import threading
        print("ConnectionManager: Reloading server subprocess lifecycles in background...")
        thread = threading.Thread(target=self._reload_connections_thread, daemon=True)
        thread.start()

    def _reload_connections_thread(self):
        # 1. Filesystem MCP
        fs_root = mcp_settings.get("filesystem_root")
        if fs_root and os.path.exists(fs_root):
            # npx filesystem command
            cmd = ["npx", "-y", "@modelcontextprotocol/server-filesystem", fs_root]
            self.connect_server("filesystem_mcp", cmd)

        # 2. GitHub MCP
        gh_token = mcp_settings.get("github_token")
        if gh_token:
            cmd = ["npx", "-y", "@modelcontextprotocol/server-github"]
            self.connect_server("github_mcp", cmd, env={"GITHUB_PERSONAL_ACCESS_TOKEN": gh_token})
            
        # 3. Browser MCP
        # Playwright crawler command
        self.connect_server("browser_mcp", ["npx", "-y", "@modelcontextprotocol/server-playwright"])
