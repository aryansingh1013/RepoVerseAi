import os
from typing import List, Dict, Any
from backend.mcp.manager import MCPSubprocessServer
from backend.mcp.config import mcp_settings

class GitHubMCPServer(MCPSubprocessServer):
    """
    Subprocess wrapper for the official @modelcontextprotocol/server-github npm package.
    """
    def __init__(self):
        token = mcp_settings.get("github_token", "")
        command = ["npx", "-y", "@modelcontextprotocol/server-github"]
        
        env = {}
        if token:
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = token
            
        super().__init__(
            name="github_mcp",
            command=command,
            env=env if token else None,
            timeout=mcp_settings.get("connection_timeout", 30)
        )
