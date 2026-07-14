from pydantic import BaseModel, Field
from typing import Dict, Any, List
from backend.agent.permissions import PermissionType

class Capability(BaseModel):
    name: str = Field(..., description="Unique name of the capability (e.g. read_file, git_log)")
    description: str = Field(..., description="Description of what this capability does, used by the planner")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, 
        description="JSON Schema defining required and optional input arguments"
    )
    permissions: List[PermissionType] = Field(
        default_factory=list,
        description="List of security permission tokens required to execute this capability"
    )
