from abc import ABC, abstractmethod
from typing import List, Dict, Any
from backend.agent.capabilities import Capability
from backend.agent.tool_models import ToolResult

class IMCPServer(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initializes the MCP server. Resolves dependencies, sets up local sandboxes,
        or spawns standard subprocess connections.
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        pass

    @abstractmethod
    def discover_capabilities(self) -> List[Capability]:
        """
        Discovers the capability definitions this server exposes.
        Returns:
            List[Capability]: List of Capability objects.
        """
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """
        Checks health status of the server.
        Returns:
            Dict[str, Any]: Telemetry metrics containing keys like 'status' (healthy/unhealthy),
                            'uptime_seconds', 'latency_ms', and 'errors'.
        """
        pass

    @abstractmethod
    def execute(self, capability: str, args: Dict[str, Any]) -> ToolResult:
        """
        Executes a specific capability.
        Args:
            capability (str): Capability name to run.
            args (Dict[str, Any]): Argument payload mapping.
        Returns:
            ToolResult: Unified execution result format.
        """
        pass

    @abstractmethod
    def shutdown(self) -> bool:
        """
        Cleans up handles, socket connections, file descriptors, or child processes.
        Returns:
            bool: True if cleanup was successful, False otherwise.
        """
        pass
