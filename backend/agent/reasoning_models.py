from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Goal(BaseModel):
    intent: str = Field(..., description="Intent classification (e.g. explain, debug, comparison)")
    expected_output: str = Field(..., description="Description of the target outcome")
    required_knowledge: List[str] = Field(default_factory=list, description="Target folders/topics needed")
    risk_level: str = Field(default="low", description="Assessed risk level: low, medium, high")
    confidence: float = Field(default=1.0, description="Base confidence scoring")

class Task(BaseModel):
    task_id: str = Field(..., description="Unique alphanumeric identifier (e.g., task_0, task_1)")
    description: str = Field(..., description="Actionable task description")
    status: str = Field(default="pending", description="Status: pending, running, success, failed")
    dependencies: List[str] = Field(default_factory=list, description="List of task IDs that must complete first")
    capabilities_needed: List[str] = Field(default_factory=list, description="List of capability names required")
    priority: int = Field(default=1, description="Execution priority ordering")
    expected_output: str = Field(..., description="Expected output description")
    output_payload: Optional[Any] = Field(default=None, description="Actual output result of the task execution")
    latency_ms: Optional[float] = Field(default=None, description="Measured execution time in milliseconds")

class ExecutionPlan(BaseModel):
    goal: Goal
    tasks: List[Task] = Field(default_factory=list)
    parallel_groups: List[List[str]] = Field(default_factory=list, description="List of groups containing independent task IDs that can run concurrently")
    confidence_score: float = Field(default=1.0)

class ExecutionMemory(BaseModel):
    goal: Goal
    tasks: List[Task] = Field(default_factory=list)
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Serialized results list")
    failures: List[str] = Field(default_factory=list, description="Capability or task execution failure logs")
    execution_time_ms: float = Field(default=0.0)
    reasoning_trace: List[str] = Field(default_factory=list, description="High-level list of steps taken during execution")
