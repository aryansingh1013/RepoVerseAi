from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseSkill(ABC):
    """
    Abstract Base Class for all AI Workflows (Skills) in RepoVerse AI.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """The user-friendly name of the skill."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A detailed explanation of what this skill accomplishes."""
        pass

    @property
    @abstractmethod
    def required_capabilities(self) -> List[str]:
        """Abstract list of tool capability slugs needed (e.g. read_file, git_log)."""
        pass

    @property
    @abstractmethod
    def result_schema(self) -> Dict[str, Any]:
        """JSON schema describing the structured dictionary returned by execute()."""
        pass

    @abstractmethod
    def execute(self, query: str, agent_graph: Any, workspace_dir: str) -> Dict[str, Any]:
        """
        Executes the specialized workflow using Planner/RAG/MCP nodes.
        Returns a dictionary conforming to self.result_schema.
        """
        pass
