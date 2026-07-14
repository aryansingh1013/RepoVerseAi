from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class ToolResult(BaseModel):
    tool_name: str = Field(..., description="Name of the MCP server that executed the tool")
    capability: str = Field(..., description="Name of the executed capability")
    status: str = Field(..., description="Status string: success, error, timeout, permission_denied, etc.")
    latency_ms: float = Field(..., description="Total execution latency in milliseconds")
    result: Optional[Any] = Field(default=None, description="Actual output payload of the tool execution")
    errors: Optional[List[str]] = Field(default=None, description="List of error messages if execution failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional debugging or tracking metadata")

class ExecutionLog(BaseModel):
    execution_id: str = Field(..., description="Unique ID tracking this capability call execution")
    capability: str = Field(..., description="Capability name")
    tool_selected: str = Field(..., description="Name of the chosen tool provider")
    latency_ms: float = Field(..., description="Latency measured in milliseconds")
    status: str = Field(..., description="Status outcome of execution")
    errors: Optional[List[str]] = Field(default=None, description="List of error logs if failed")
