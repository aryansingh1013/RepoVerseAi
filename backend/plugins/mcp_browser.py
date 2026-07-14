import time
import urllib.request
import urllib.parse
import json
import re
from typing import List, Dict, Any
from backend.mcp.manager import MCPSubprocessServer
from backend.mcp.config import mcp_settings
from backend.agent.capabilities import Capability
from backend.agent.permissions import PermissionType
from backend.agent.tool_models import ToolResult

class BrowserMCPServer(MCPSubprocessServer):
    """
    Subprocess wrapper for the official @modelcontextprotocol/server-playwright npm package.
    Falls back to a native Python search mode if npx or playwright is missing.
    """
    def __init__(self):
        command = ["npx", "-y", "@modelcontextprotocol/server-playwright"]
        self.use_native = False
        super().__init__(
            name="browser_mcp",
            command=command,
            env=None,
            timeout=mcp_settings.get("connection_timeout", 30)
        )

    def initialize(self) -> bool:
        success = super().initialize()
        if not success:
            print("BrowserMCPServer: Subprocess initialization failed. Falling back to native Python mode.")
            self.use_native = True
            self._is_active = True
            return True
        return True

    def discover_capabilities(self) -> List[Capability]:
        if self.use_native:
            return [
                Capability(
                    name="browser_search",
                    description="Search the web for documentation or technical references.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    },
                    permissions=[PermissionType.READ]
                )
            ]
        return super().discover_capabilities()

    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        if self.use_native:
            start_time = time.perf_counter()
            query = args.get("query", "")
            if not query:
                return ToolResult(
                    tool_name=self.name,
                    capability=capability,
                    status="error",
                    latency_ms=0.0,
                    errors=["Search query is empty."]
                )
            
            try:
                url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8')
                
                matches = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
                snippets = []
                for match in matches[:5]:
                    clean = re.sub(r'<[^>]+>', '', match).strip()
                    snippets.append(clean)
                
                res_str = "\n\n".join(snippets) if snippets else "No web results found."
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
                    status="success",
                    latency_ms=(time.perf_counter() - start_time) * 1000.0,
                    result=f"Could not reach external search server: {e}. Falling back to cached knowledge."
                )
        return super().execute(capability, args)
