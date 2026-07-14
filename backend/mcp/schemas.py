from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class MCPServerConfig(BaseModel):
    name: str = Field(..., description="Unique slug identifying this MCP Server (e.g., git_mcp)")
    enabled: bool = Field(default=True, description="Enable or disable the server")
    timeout_seconds: int = Field(default=30, description="Default execution timeout boundary")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables passed during initialization")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Custom dictionary for server-specific variables")
