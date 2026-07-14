import time
from typing import Dict, Any, List
from backend.agent.state import AgentState
from backend.agent.registry import AgentToolRegistry
from backend.agent.tool_models import ToolResult

class ExecutorNode:
    def __init__(self, agent_registry: AgentToolRegistry):
        self.agent_registry = agent_registry

    def execute(self, state: AgentState) -> Dict[str, Any]:
        requests = state.get("capability_requests", [])
        steps = state.get("agent_steps", [])
        tool_outputs = state.get("tool_outputs", [])

        if not requests:
            steps.append("⚙️ Executor: No capability requests to execute.")
            return {"agent_steps": steps, "tool_outputs": tool_outputs}

        steps.append(f"⚙️ Executor: Processing {len(requests)} capability requests...")

        for req in requests:
            cap_name = req.get("capability")
            cap_args = req.get("args", {})

            if not cap_name:
                continue

            steps.append(f"Running capability: '{cap_name}' with args {cap_args}...")
            
            # Execute through the AgentToolRegistry
            # This handles lookup, permissions, health, exception trapping, and latency tracking.
            tool_result: ToolResult = self.agent_registry.execute_agent_capability(cap_name, cap_args)
            
            # Record outcome in steps
            steps.append(
                f"Capability '{cap_name}' finished with status [{tool_result.status}] "
                f"in {tool_result.latency_ms:.1f}ms."
            )
            
            # Add to tool outputs as serialized JSON string or structured log
            log_output = (
                f"--- Tool Call: {tool_result.tool_name} ({tool_result.capability}) ---\n"
                f"Status: {tool_result.status} | Latency: {tool_result.latency_ms:.1f}ms\n"
                f"Result: {tool_result.result}\n"
            )
            if tool_result.errors:
                log_output += f"Errors: {', '.join(tool_result.errors)}\n"
                
            tool_outputs.append(log_output)

        steps.append("⚙️ Executor: Finished executing all requested capabilities.")
        
        return {
            "tool_outputs": tool_outputs,
            "agent_steps": steps
        }
