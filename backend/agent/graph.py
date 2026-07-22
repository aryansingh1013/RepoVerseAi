from langgraph.graph import StateGraph, END
from backend.agent.state import AgentState
from backend.agent.nodes import AgentNodes

def create_agent_graph(nodes: AgentNodes) -> StateGraph:
    """
    Assembles nodes into an advanced 10-node LangGraph Cognitive orchestration workflow.
    """
    workflow = StateGraph(AgentState)

    # 1. Register nodes
    workflow.add_node("intent_classifier", nodes.intent_classifier)
    workflow.add_node("goal_analyzer", nodes.goal_analyzer_node)
    workflow.add_node("task_decomposer", nodes.task_decomposer_node)
    workflow.add_node("planner_v2", nodes.planner_v2_node)
    workflow.add_node("retriever", nodes.retriever_node)
    workflow.add_node("executor", nodes.parallel_executor_node)
    workflow.add_node("result_fusion", nodes.result_fusion_node)
    workflow.add_node("reflection", nodes.reflection_node)
    workflow.add_node("generator", nodes.generator)
    workflow.add_node("verify", nodes.verification_node)

    # 2. Setup linear edges
    workflow.set_entry_point("intent_classifier")
    
    def after_intent_routing(state: AgentState) -> str:
        if state.get("out_of_context", False):
            return END
        return "goal_analyzer"
        
    workflow.add_conditional_edges(
        "intent_classifier",
        after_intent_routing,
        {
            "goal_analyzer": "goal_analyzer",
            END: END
        }
    )
    workflow.add_edge("goal_analyzer", "task_decomposer")
    workflow.add_edge("task_decomposer", "planner_v2")
    workflow.add_edge("planner_v2", "retriever")
    workflow.add_edge("retriever", "executor")
    workflow.add_edge("executor", "result_fusion")
    workflow.add_edge("result_fusion", "reflection")

    # 3. Setup conditional routing for Reflection loop (Dynamic Re-planning)
    def reflection_routing(state: AgentState) -> str:
        status = state.get("reflection_status", {})
        need_replanning = status.get("need_replanning", False)
        retries = state.get("retries", 0)
        
        if need_replanning and retries < 2:
            state["agent_steps"].append(f"🔁 Reflection Check: replanning required (Retry {retries+1}/2). Routing back...")
            return "task_decomposer"
            
        return "generator"

    workflow.add_conditional_edges(
        "reflection",
        reflection_routing,
        {
            "task_decomposer": "task_decomposer",
            "generator": "generator"
        }
    )

    workflow.add_edge("generator", "verify")

    # 4. Setup conditional routing for Verification (Fact Checker) Node
    def verify_routing(state: AgentState) -> str:
        is_verified = state.get("is_verified", True)
        retries = state.get("retries", 0)
        
        if not is_verified and retries < 2:
            state["agent_steps"].append(f"🔁 Fact-checking failed. Re-routing back (Retry {retries}/2)...")
            return "goal_analyzer"
            
        return END

    workflow.add_conditional_edges(
        "verify",
        verify_routing,
        {
            "goal_analyzer": "goal_analyzer",
            END: END
        }
    )

    # 5. Compile
    return workflow.compile()
