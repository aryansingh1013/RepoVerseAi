import json
import re
from typing import Dict, Any, List
from backend.agent.state import AgentState
from backend.agent.registry import AgentToolRegistry

class PlannerNode:
    def __init__(self, agent_registry: AgentToolRegistry, llm_caller=None):
        self.agent_registry = agent_registry
        self.llm_caller = llm_caller # Callable helper from AgentNodes

    def plan(self, state: AgentState) -> Dict[str, Any]:
        query = state["query"]
        steps = state.get("agent_steps", [])
        steps.append("🧠 Planner: Formulating capability requests...")

        # 1. Gather all registered capabilities from the registry
        capabilities = self.agent_registry.get_available_capabilities_metadata()
        
        # 2. Build system instructions for LLM Planner
        capabilities_list_str = ""
        for cap in capabilities:
            capabilities_list_str += (
                f"- Name: {cap['name']}\n"
                f"  Description: {cap['description']}\n"
                f"  Args Schema: {json.dumps(cap['input_schema'])}\n"
                f"  Required Permissions: {cap['permissions']}\n"
            )

        system_prompt = (
            "You are RepoVerse AI Planner Node.\n"
            "Your job is to analyze the user's query and decide which capabilities (tools) are required to answer it.\n"
            "You MUST output a JSON object containing a list of capability requests:\n"
            "{\n"
            "  \"reasoning\": \"Why these capabilities are needed\",\n"
            "  \"requests\": [\n"
            "     { \"capability\": \"capability_name\", \"args\": { ... } }\n"
            "  ]\n"
            "}\n\n"
            "Available capabilities in the Tool Registry:\n"
            f"{capabilities_list_str}\n\n"
            "Rules:\n"
            "1. Output ONLY the raw JSON object.\n"
            "2. If no tools/capabilities are needed to answer the query, return requests as an empty list [].\n"
            "3. Do not formulate calls to tools that are not in the list."
        )

        capability_requests = []
        
        # 3. Call LLM
        if self.llm_caller:
            response_text = self.llm_caller([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}"}
            ], json_mode=True)
            
            if response_text:
                try:
                    plan_data = json.loads(response_text)
                    capability_requests = plan_data.get("requests", [])
                    reasoning = plan_data.get("reasoning", "")
                    if reasoning:
                        steps.append(f"Planner Reasoning: {reasoning}")
                except Exception:
                    pass

        # 4. Heuristics Fallback if LLM offline / no requests resolved
        if not capability_requests:
            query_lower = query.lower()
            # Simple keyword matching to registered capability names
            if "git log" in query_lower or "commits" in query_lower:
                capability_requests.append({"capability": "git_log", "args": {"limit": 5}})
            elif "git diff" in query_lower or "changes" in query_lower:
                capability_requests.append({"capability": "git_diff", "args": {}})
            elif "list files" in query_lower or "ls " in query_lower:
                capability_requests.append({"capability": "filesystem_list", "args": {"relative_path": "."}})
            elif "search" in query_lower or "google" in query_lower:
                # search query
                search_term = query.replace("search", "").strip()
                capability_requests.append({"capability": "browser_search", "args": {"query": search_term}})
            elif "run test" in query_lower or "pytest" in query_lower:
                capability_requests.append({"capability": "terminal_run", "args": {"command": "pytest"}})

        # Save capability requests in agent steps for UI
        if capability_requests:
            req_names = [r["capability"] for r in capability_requests]
            steps.append(f"Planner planned {len(capability_requests)} requests: {', '.join(req_names)}")
        else:
            steps.append("Planner: No tool execution capabilities required.")

        return {
            "capability_requests": capability_requests,
            "agent_steps": steps
        }
