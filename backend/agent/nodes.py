import os
import json
import re
import time
from typing import Dict, Any, List
from openai import OpenAI
from backend.agent.state import AgentState
from backend.rag.retriever import HybridRetriever
from backend.mcp.tools import MCPTools
from backend.core.config import settings

class AgentNodes:
    def __init__(self, retriever: HybridRetriever, workspace_dir: str, agent_registry):
        self.retriever = retriever
        self.tools = MCPTools(workspace_dir)
        self.agent_registry = agent_registry
        self._init_llm_client()
        
        # Instantiate Cognitive Layer subcomponents (Phase 3)
        from backend.agent.goal_analyzer import GoalAnalyzer
        from backend.agent.task_decomposer import TaskDecomposer
        from backend.agent.planner_v2 import PlannerV2
        from backend.agent.parallel_executor import ParallelExecutor
        from backend.agent.result_fusion import ResultFusion
        from backend.agent.reflection import ReflectionNode
        from backend.agent.execution_memory import ExecutionMemoryTracker

        self.goal_analyzer = GoalAnalyzer(llm_caller=None)
        self.task_decomposer = TaskDecomposer(llm_caller=None)
        self.planner_v2 = PlannerV2()
        self.parallel_executor = ParallelExecutor(self.agent_registry)
        self.result_fusion = ResultFusion()
        self.reflection = ReflectionNode(llm_caller=None)
        self.memory = ExecutionMemoryTracker()
        self.start_time = 0.0

    def goal_analyzer_node(self, state: AgentState) -> Dict[str, Any]:
        query = state["query"]
        steps = state.get("agent_steps", [])
        steps.append("🧠 Goal Analyzer: Assessing query goals and risks...")
        self.start_time = time.perf_counter()
        
        goal = self.goal_analyzer.analyze_goal(query)
        steps.append(f"Goal Analysed: intent='{goal.intent}', risk='{goal.risk_level}', output='{goal.expected_output}'")
        
        serialized_goal = {
            "intent": goal.intent,
            "expected_output": goal.expected_output,
            "risk_level": goal.risk_level,
            "confidence": goal.confidence
        }
        return {
            "goal_metadata": serialized_goal,
            "agent_steps": steps
        }

    def task_decomposer_node(self, state: AgentState) -> Dict[str, Any]:
        query = state["query"]
        steps = state.get("agent_steps", [])
        steps.append("🧠 Decomposer: Formulating tasks graph...")
        
        from backend.agent.reasoning_models import Goal
        g_meta = state.get("goal_metadata", {})
        goal = Goal(
            intent=g_meta.get("intent", "general"),
            expected_output=g_meta.get("expected_output", ""),
            risk_level=g_meta.get("risk_level", "low"),
            confidence=g_meta.get("confidence", 1.0)
        )
        
        tasks = self.task_decomposer.decompose(goal, query)
        steps.append(f"Decomposed query into {len(tasks)} target subtasks.")
        
        serialized_tasks = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "status": t.status,
                "dependencies": t.dependencies,
                "capabilities": t.capabilities_needed,
                "latency_ms": t.latency_ms
            }
            for t in tasks
        ]
        return {
            "tasks_metadata": serialized_tasks,
            "agent_steps": steps
        }

    def planner_v2_node(self, state: AgentState) -> Dict[str, Any]:
        steps = state.get("agent_steps", [])
        steps.append("🧠 Planner V2: Computing dependency layers...")
        
        from backend.agent.reasoning_models import Goal, Task
        g_meta = state.get("goal_metadata", {})
        goal = Goal(
            intent=g_meta.get("intent", "general"),
            expected_output=g_meta.get("expected_output", ""),
            risk_level=g_meta.get("risk_level", "low"),
            confidence=g_meta.get("confidence", 1.0)
        )
        
        tasks = [
            Task(
                task_id=t.get("task_id"),
                description=t.get("description"),
                status=t.get("status", "pending"),
                dependencies=t.get("dependencies", []),
                capabilities_needed=t.get("capabilities", []),
                expected_output=""
            )
            for t in state.get("tasks_metadata", [])
        ]
        
        plan = self.planner_v2.generate_execution_strategy(goal, tasks)
        steps.append(f"Planner V2: Resolved parallel groups: {plan.parallel_groups}")
        
        # Build abstract capability requests for backwards compatibility
        cap_reqs = []
        for t in plan.tasks:
            for cap in t.capabilities_needed:
                cap_reqs.append({"capability": cap, "args": {}})

        return {
            "capability_requests": cap_reqs,
            "agent_steps": steps,
            "goal_metadata": {**g_meta, "parallel_groups": plan.parallel_groups}
        }

    def parallel_executor_node(self, state: AgentState) -> Dict[str, Any]:
        steps = state.get("agent_steps", [])
        steps.append("⚙️ Executor: Resolving parallel capability calls...")
        
        from backend.agent.reasoning_models import Goal, Task, ExecutionPlan
        g_meta = state.get("goal_metadata", {})
        goal = Goal(
            intent=g_meta.get("intent", "general"),
            expected_output=g_meta.get("expected_output", ""),
            risk_level=g_meta.get("risk_level", "low"),
            confidence=g_meta.get("confidence", 1.0)
        )
        
        tasks = [
            Task(
                task_id=t.get("task_id"),
                description=t.get("description"),
                status=t.get("status", "pending"),
                dependencies=t.get("dependencies", []),
                capabilities_needed=t.get("capabilities", []),
                expected_output=""
            )
            for t in state.get("tasks_metadata", [])
        ]
        
        plan = ExecutionPlan(
            goal=goal,
            tasks=tasks,
            parallel_groups=g_meta.get("parallel_groups", [])
        )
        
        executed_tasks = self.parallel_executor.execute_plan(plan, steps)
        
        serialized_tasks = [
            {
                "task_id": t.task_id,
                "description": t.description,
                "status": t.status,
                "dependencies": t.dependencies,
                "capabilities": t.capabilities_needed,
                "latency_ms": t.latency_ms,
                "output_payload": t.output_payload
            }
            for t in executed_tasks
        ]
        
        return {
            "tasks_metadata": serialized_tasks,
            "agent_steps": steps
        }

    def result_fusion_node(self, state: AgentState) -> Dict[str, Any]:
        steps = state.get("agent_steps", [])
        steps.append("🧬 Result Fusion: Consolidating and ranking contexts...")
        
        from backend.agent.reasoning_models import Task
        tasks = [
            Task(
                task_id=t.get("task_id"),
                description=t.get("description"),
                status=t.get("status", "pending"),
                dependencies=t.get("dependencies", []),
                capabilities_needed=t.get("capabilities", []),
                expected_output="",
                output_payload=t.get("output_payload")
            )
            for t in state.get("tasks_metadata", [])
        ]
        
        rag_contexts = state.get("retrieved_contexts", [])
        fused = self.result_fusion.fuse_contexts(tasks, rag_contexts)
        steps.append(f"Result Fusion: Consolidated {len(fused.get('contexts', []))} relevant chunks.")
        
        return {
            "retrieved_contexts": fused.get("contexts", []),
            "agent_steps": steps
        }

    def reflection_node(self, state: AgentState) -> Dict[str, Any]:
        steps = state.get("agent_steps", [])
        steps.append("🛡️ Reflection: Evaluating answer coverage...")
        
        from backend.agent.reasoning_models import Goal, Task
        g_meta = state.get("goal_metadata", {})
        goal = Goal(
            intent=g_meta.get("intent", "general"),
            expected_output=g_meta.get("expected_output", ""),
            risk_level=g_meta.get("risk_level", "low"),
            confidence=g_meta.get("confidence", 1.0)
        )
        
        tasks = [
            Task(
                task_id=t.get("task_id"),
                description=t.get("description"),
                status=t.get("status", "pending"),
                dependencies=t.get("dependencies", []),
                capabilities_needed=t.get("capabilities", []),
                expected_output="",
                output_payload=t.get("output_payload")
            )
            for t in state.get("tasks_metadata", [])
        ]
        
        fused_contexts = {"contexts": state.get("retrieved_contexts", [])}
        retries = state.get("retries", 0)
        
        refl_res = self.reflection.evaluate_coverage(goal, tasks, fused_contexts, retries)
        steps.append(f"Reflection Check: need_replanning={refl_res['need_replanning']}, reason='{refl_res['reason']}'")
        
        # Compile Reasoning Trace
        end_time = time.perf_counter()
        total_time_ms = (end_time - self.start_time) * 1000.0
        
        trace = self.memory.compile_reasoning_trace(goal, tasks, [refl_res["reason"]])
        self.memory.save_run(goal, tasks, total_time_ms, trace)
        
        return {
            "reflection_status": {
                "need_replanning": refl_res.get("need_replanning", False),
                "confidence": refl_res.get("confidence", 1.0),
                "reason": refl_res.get("reason", "")
            },
            "reasoning_trace": trace,
            "retries": retries + (1 if refl_res.get("need_replanning", False) else 0)
        }

    def _init_llm_client(self):
        """Resolves active primary model from ModelRouter configuration."""
        from backend.llm.model_router import model_router
        from backend.llm.task_router import task_router
        prov, model = task_router.resolve_task("chat")
        self.model_name = f"{prov} / {model}"
        print(f"Agent Nodes initialized. Primary task target is: {self.model_name}")

    def _call_llm(self, messages: List[Dict[str, str]], temperature: float = 0.1, json_mode: bool = False, task: str = "chat") -> str:
        """Central gate routing LLM requests through the centralized ModelRouter."""
        from backend.llm.model_router import model_router
        res = model_router.generate(
            task=task,
            messages=messages,
            temperature=temperature,
            json_mode=json_mode
        )
        self.model_name = f"{res.provider} / {res.model}"
        return res.response

    # Node 1: Intent Classifier
    def intent_classifier(self, state: AgentState) -> AgentState:
        query = state["query"]
        steps = state.get("agent_steps", [])
        steps.append("🚀 Classifying query intent (Pure Python)...")

        query_lower = query.lower()
        
        # Retrieval markers
        retrieval_keywords = [
            "find", "search", "where", "how is", "show", "code", "file", 
            "function", "class", "imports", "exports", "explain", "why", "implement"
        ]
        needs_retrieval = any(k in query_lower for k in retrieval_keywords) or len(query) > 10
        
        # Tool markers
        tool_keywords = [
            "run", "pytest", "test", "git", "log", "diff", "execute", "terminal", 
            "npm run build", "build", "shell", "exec", "list", "folder", "directory", "ls", "files in", "whats in", "what is in", "contents of"
        ]
        needs_tool = any(k in query_lower for k in tool_keywords)

        steps.append(f"Intent classified: needs_retrieval={needs_retrieval}, needs_tool={needs_tool}")
        
        return {
            **state,
            "needs_retrieval": needs_retrieval,
            "needs_tool": needs_tool,
            "agent_steps": steps
        }

    # Node 2: Retriever Node
    def retriever_node(self, state: AgentState) -> AgentState:
        query = state["query"]
        steps = state.get("agent_steps", [])
        
        if not state.get("needs_retrieval", False):
            steps.append("⏭️ Skipping retrieval (not needed).")
            return {**state, "agent_steps": steps}

        steps.append("🔍 Fetching code snippets via Hybrid Vector+BM25...")
        
        # Simple extraction of filters (e.g. if query mentions a specific file)
        where_filter = None
        file_match = re.search(r"in\s+([a-zA-Z0-9_\-\.\/]+)", query, re.IGNORECASE)
        if file_match:
            filename = file_match.group(1)
            # Try to filter by path if it looks like a filename
            if "." in filename:
                where_filter = {"path": filename}
                steps.append(f"Applying metadata path filter: {filename}")

        retrieved = self.retriever.retrieve(query, limit=5, where_filter=where_filter)
        
        steps.append(f"Retrieved {len(retrieved)} relevant codebase chunks.")
        
        return {
            **state,
            "retrieved_contexts": retrieved,
            "agent_steps": steps
        }

    # Node 3: MCP Tool Node
    def mcp_node(self, state: AgentState) -> AgentState:
        query = state["query"]
        steps = state.get("agent_steps", [])
        
        if not state.get("needs_tool", False):
            steps.append("⏭️ Skipping tool execution (not requested).")
            return {**state, "agent_steps": steps}
            
        steps.append("🛠️ Resolving and executing workspace tools...")
        tool_outputs = state.get("tool_outputs", [])

        # LLM based tool invocation
        system_prompt = (
            "You are RepoVerse Tool Selector. Choose the correct tool to run based on the user's query.\n"
            "Available tools:\n"
            "1. filesystem_list (relative_path: str)\n"
            "2. filesystem_read (relative_path: str, start_line: int, end_line: int)\n"
            "3. git_log (limit: int)\n"
            "4. git_diff (file_path: str)\n"
            "5. terminal_run (command: str) - ONLY supports 'pytest' or 'npm run build'\n"
            "6. python_execute (code: str) - Executes python code snippet in temporary file\n"
            "7. browser_search (query: str) - Search web docs\n\n"
            "Respond ONLY with a JSON object: {\"tool\": \"name\", \"args\": { ... }}"
        )
        
        response_text = self._call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}"}
        ], json_mode=True, task="tool_selection")
        
        tool_name = ""
        tool_args = {}
        
        if response_text:
            try:
                call_info = json.loads(response_text)
                tool_name = call_info.get("tool", "")
                tool_args = call_info.get("args", {})
            except Exception:
                pass
                
        # Heuristics Fallback if LLM is offline/errored
        if not tool_name:
            query_lower = query.lower()
            if "pytest" in query_lower:
                tool_name = "terminal_run"
                tool_args = {"command": "pytest"}
            elif "git log" in query_lower:
                tool_name = "git_log"
                tool_args = {"limit": 5}
            elif "git diff" in query_lower:
                tool_name = "git_diff"
                tool_args = {}
            elif "list files" in query_lower or "ls" in query_lower:
                tool_name = "filesystem_list"
                tool_args = {"relative_path": "."}
            elif "search" in query_lower:
                tool_name = "browser_search"
                tool_args = {"query": query}

        if tool_name:
            steps.append(f"Executing tool {tool_name} with arguments: {tool_args}")
            output = self.tools.execute_tool(tool_name, tool_args)
            # Truncate large tool output to prevent token explosion
            if len(output) > 2000:
                output = output[:2000] + "\n... [Output Truncated] ..."
            tool_outputs.append(f"Tool [{tool_name}] output:\n{output}")
        else:
            steps.append("No suitable tool resolved to run.")

        return {
            **state,
            "tool_outputs": tool_outputs,
            "agent_steps": steps
        }

    # Node 4: Generation Node
    def generator(self, state: AgentState) -> AgentState:
        query = state["query"]
        contexts = state.get("retrieved_contexts", [])
        tool_outputs = state.get("tool_outputs", [])
        steps = state.get("agent_steps", [])
        steps.append("✍️ Synthesizing response grounded in codebase context...")

        # Build context prompt
        context_str = ""
        if contexts:
            context_str += "=== RETRIEVED CODE CONTEXTS ===\n"
            for c in contexts:
                meta = c.get("metadata", {})
                path = meta.get("path") if meta else None
                if path:
                    context_str += f"File: {path} | Start: {meta.get('start_line', 1)} | End: {meta.get('end_line', 1)}\n"
                else:
                    context_str += f"Source: {c.get('source', 'unknown')} | Tool: {meta.get('tool', 'unknown')} | Capability: {meta.get('capability', 'unknown')}\n"
                
                if meta and meta.get("class"):
                    context_str += f"Class: {meta['class']}\n"
                if meta and meta.get("function"):
                    context_str += f"Function: {meta['function']}\n"
                context_str += f"Code:\n{c.content if hasattr(c, 'content') else c.get('content', '')}\n"
                context_str += "-" * 40 + "\n"

        if tool_outputs:
            context_str += "\n=== TOOL EXECUTION OUTPUTS ===\n"
            for out in tool_outputs:
                context_str += out + "\n"
                context_str += "-" * 40 + "\n"

        system_prompt = (
            "You are RepoVerse AI Assistant, acting as a patient, expert coding teacher and guide.\n"
            "Your task is to explain codebase concepts and answer the user's questions in a clear, easy-to-understand layman form so even a beginner or newbie with no prior coding experience can understand everything.\n"
            "Rules:\n"
            "1. Be a patient, encouraging teacher. Break down complex programming concepts, files, and algorithms using simple analogies and step-by-step explanations.\n"
            "2. Always provide concrete, beginner-friendly code examples and references to explain how parts of the codebase work.\n"
            "3. Answer accuracy is critical. Do not hallucinate classes, functions, or variables.\n"
            "4. Ground every single claim with explicit markdown citations pointing to the files (Planets) or functions/classes (Moons).\n"
            "5. Citation format: Use `[Planet: relative/path/to/file, lines x-y]` or `[Moon: ClassName.method_name]` in line with text.\n"
            "6. Keep the space theme active (e.g. Constellation, Star, Planet, Moon) where appropriate but prioritize clarity and educational value.\n"
            "7. If you do not have enough context, state it clearly."
        )

        user_prompt = f"Context:\n{context_str}\n\nUser Question: {query}"
        
        # Call LLM
        response = self._call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ], temperature=0.2, task="chat")

        # Basic text fallback if LLM offline/empty
        if not response:
            steps.append("⚠️ LLM failed, using fallback summary.")
            if contexts:
                summary_files = list(set([c["metadata"]["path"] for c in contexts if c.get("metadata") and "path" in c["metadata"]]))
                response = (
                    f"I retrieved information from {', '.join(summary_files)} but could not synthesize a custom response because the AI model is currently offline or rate-limited.\n\n"
                    "⚠️ **Troubleshooting Tip**: The shared Groq API Key has reached its daily rate limit (429 Rate Limit Exceeded).\n"
                    "Please click the **Settings icon (⚙️)** in the top-right navbar and:\n"
                    "1. Input your own personal Groq API Key or OpenAI API Key.\n"
                    "2. Or, start a local Ollama server (`ollama run qwen2.5`) which is free and has no limits."
                    "\n\nHere is a list of relevant files and locations found:\n"
                )
                for c in contexts:
                    meta = c["metadata"]
                    response += f"- [Planet: {meta['path']}] line range {meta['start_line']}-{meta['end_line']} ({meta['chunk_type']})\n"
            else:
                response = (
                    "I couldn't retrieve any relevant codebase context to answer your question. "
                    "Please verify that the files are indexed correctly.\n\n"
                    "⚠️ **Note**: The AI model is currently rate-limited or offline. Please input a valid API Key in the Settings Panel (⚙️)."
                )

        # Parse citations out of response
        citations = []
        matches = re.findall(r"\[Planet:\s*([^,\]]+),\s*lines?\s*(\d+(?:-\d+)?)\]", response, re.IGNORECASE)
        for path, lines in matches:
            citations.append({
                "type": "planet",
                "path": path.strip(),
                "lines": lines.strip()
            })
            
        matches_moons = re.findall(r"\[Moon:\s*([^\]]+)\]", response, re.IGNORECASE)
        for symbol in matches_moons:
            citations.append({
                "type": "moon",
                "symbol": symbol.strip()
            })

        # Deduplicate citations
        unique_citations = []
        seen = set()
        for cit in citations:
            key = f"{cit.get('path') or cit.get('symbol')}"
            if key not in seen:
                seen.add(key)
                unique_citations.append(cit)

        # Convert raw Planet citations to beautiful clickable links
        workspace_url_base = settings.WORKSPACE_DIR.replace("\\", "/").lstrip("/")
        
        def replace_planet_citation(match):
            path = match.group(1).strip()
            lines = match.group(2).strip()
            link_path = path.replace("\\", "/")
            
            # Anchor format
            anchor = ""
            if "-" in lines:
                parts = lines.split("-")
                if len(parts) == 2:
                    anchor = f"#L{parts[0]}-L{parts[1]}"
                else:
                    anchor = f"#L{lines}"
            else:
                anchor = f"#L{lines}"
                
            return f"[{path} (L{lines})](file:///{workspace_url_base}/{link_path}{anchor})"

        response = re.sub(
            r"\[Planet:\s*([^,\]]+),\s*lines?\s*(\d+(?:-\d+)?)\]",
            replace_planet_citation,
            response,
            flags=re.IGNORECASE
        )

        response = re.sub(
            r"\[Moon:\s*([^\]]+)\]",
            lambda m: f"**{m.group(1).strip()}**",
            response,
            flags=re.IGNORECASE
        )

        steps.append(f"Response generated with {len(unique_citations)} citations.")

        return {
            **state,
            "response": response,
            "citations": unique_citations,
            "agent_steps": steps
        }

    # Node 5: Verification (Fact Checker) Node
    def verification_node(self, state: AgentState) -> AgentState:
        response = state.get("response", "")
        contexts = state.get("retrieved_contexts", [])
        steps = state.get("agent_steps", [])
        retries = state.get("retries", 0)
        
        steps.append("🛡️ Fact-checking and grounding verification...")

        if not contexts:
            # No context, nothing to verify
            steps.append("No context documents to verify grounding. Proceeding.")
            return {
                **state,
                "is_verified": True,
                "confidence_score": 1.0,
                "agent_steps": steps
            }

        # Extracted source filenames
        valid_paths = {c["metadata"]["path"].lower() for c in contexts if c.get("metadata") and "path" in c["metadata"]}
        valid_symbols = set()
        for c in contexts:
            meta = c.get("metadata", {})
            if meta and meta.get("class"):
                valid_symbols.add(meta["class"].lower())
            if meta and meta.get("function"):
                valid_symbols.add(meta["function"].lower())

        # Check citations against valid paths/symbols
        citations = state.get("citations", [])
        invalid_citations = []
        
        for cit in citations:
            if cit["type"] == "planet":
                path_lower = cit["path"].lower()
                # Check if it matches any indexed path (allow substring match)
                matched = any(p in path_lower or path_lower in p for p in valid_paths)
                if not matched:
                    invalid_citations.append(cit["path"])
            elif cit["type"] == "moon":
                sym_lower = cit["symbol"].lower()
                matched = any(s in sym_lower or sym_lower in s for s in valid_symbols)
                if not matched:
                    invalid_citations.append(cit["symbol"])

        is_verified = len(invalid_citations) == 0
        
        # Calculate confidence score
        if is_verified:
            confidence = 1.0
            steps.append("✅ Verification complete: Answer is grounded in retrieved codebase contexts.")
        else:
            confidence = max(0.1, 1.0 - (len(invalid_citations) * 0.25))
            steps.append(f"⚠️ Verification warning: Cited sources not present in retrieved context: {invalid_citations}")
            
        return {
            **state,
            "is_verified": is_verified,
            "confidence_score": confidence,
            "agent_steps": steps,
            "retries": retries + (1 if not is_verified else 0)
        }
