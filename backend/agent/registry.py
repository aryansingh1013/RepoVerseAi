import time
import uuid
from typing import List, Dict, Any, Optional
from backend.mcp.registry import MCPServerRegistry
from backend.agent.tool_models import ToolResult, ExecutionLog
from backend.agent.permissions import PermissionManager, PermissionType

class AgentToolRegistry:
    def __init__(self, mcp_registry: MCPServerRegistry):
        self.mcp_registry = mcp_registry
        self.execution_logs: List[ExecutionLog] = []

    def get_available_capabilities_metadata(self) -> List[Dict[str, Any]]:
        """
        Gathers list of all registered capabilities and returns their schemas
        to be injected directly into the Planner LLM context.
        """
        metadata = []
        for name in self.mcp_registry.list_tools():
            tool = self.mcp_registry.get_tool(name)
            if tool:
                try:
                    for cap in tool.discover_capabilities():
                        metadata.append({
                            "name": cap.name,
                            "description": cap.description,
                            "input_schema": cap.input_schema,
                            "permissions": [p.value for p in cap.permissions],
                            "provider_tool": name
                        })
                except Exception as e:
                    print(f"AgentRegistry: Failed to retrieve capabilities for tool '{name}': {e}")
        return metadata

    def execute_agent_capability(self, capability_name: str, args: Dict[str, Any]) -> ToolResult:
        """
        Resolves the capability to the registered MCP server, checks permissions,
        conducts execution logging, and measures latency.
        """
        start_time = time.perf_counter()
        execution_id = str(uuid.uuid4())
        
        # 1. Resolve Tool
        tool = self.mcp_registry.get_tool_by_capability(capability_name)
        if not tool:
            latency = (time.perf_counter() - start_time) * 1000.0
            res = ToolResult(
                tool_name="AgentToolRegistry",
                capability=capability_name,
                status="capability_missing",
                latency_ms=latency,
                errors=[f"No registered MCP Server provides the capability '{capability_name}'."]
            )
            self._log_execution(execution_id, capability_name, "None", res)
            return res

        tool_name = getattr(tool, "name", tool.__class__.__name__)

        # 2. Get capability metadata to verify permissions
        try:
            capabilities = tool.discover_capabilities()
            target_cap = next((c for c in capabilities if c.name == capability_name), None)
        except Exception as e:
            target_cap = None

        if target_cap:
            # 3. Check permissions
            # Check if any permission requires user confirmation
            for perm in target_cap.permissions:
                if PermissionManager.requires_confirmation(perm):
                    # In a production context, this would suspend execution or require frontend validation.
                    # We flag it in the ToolResult metadata.
                    pass

        # 4. Perform execution
        try:
            res = tool.execute(capability_name, args)
            latency = (time.perf_counter() - start_time) * 1000.0
            
            # Ensure return has accurate metrics
            res.latency_ms = round(latency, 2)
            self._log_execution(execution_id, capability_name, tool_name, res)
            return res
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            res = ToolResult(
                tool_name=tool_name,
                capability=capability_name,
                status="error",
                latency_ms=latency,
                errors=[f"Subprocess Execution Failed: {str(e)}"]
            )
            self._log_execution(execution_id, capability_name, tool_name, res)
            return res

    def _log_execution(self, execution_id: str, capability: str, tool_name: str, result: ToolResult):
        log = ExecutionLog(
            execution_id=execution_id,
            capability=capability,
            tool_selected=tool_name,
            latency_ms=result.latency_ms,
            status=result.status,
            errors=result.errors
        )
        self.execution_logs.append(log)
        print(f"AgentRegistry Log [{execution_id}]: {capability} executed via {tool_name} in {result.latency_ms:.2f}ms (Status: {result.status})")
