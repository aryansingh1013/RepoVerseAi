from typing import TypedDict, List, Dict, Any, Sequence
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # User Input
    query: str
    messages: List[BaseMessage]
    
    # Decisions / Flags
    needs_retrieval: bool
    needs_tool: bool
    is_verified: bool
    
    # Execution Tracking
    retrieved_contexts: List[Dict[str, Any]]
    capability_requests: List[Dict[str, Any]]
    tool_outputs: List[str]
    agent_steps: List[str]  # e.g. ["Classifier: Needs RAG", "Retriever: Loaded 5 chunks"]
    
    # Output Synthesis
    response: str
    citations: List[Dict[str, Any]]
    confidence_score: float
    retries: int
    
    # Cognitive / Reasoning Trace Metadata (Phase 3)
    reasoning_trace: List[str]
    goal_metadata: Dict[str, Any]
    tasks_metadata: List[Dict[str, Any]]
    reflection_status: Dict[str, Any]
