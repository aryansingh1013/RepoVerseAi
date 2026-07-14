from typing import Dict, List, Optional
from backend.mcp.interfaces import IMCPServer

class MCPServerRegistry:
    def __init__(self):
        self._tools: Dict[str, IMCPServer] = {}

    def register(self, name: str, tool: IMCPServer) -> bool:
        """Registers a tool under a given name, initializing it if needed."""
        try:
            # Try to initialize if not done
            initialized = tool.initialize()
            if not initialized:
                print(f"Registry Warning: Failed to initialize tool '{name}' during registration.")
            
            self._tools[name] = tool
            print(f"Registry: Registered tool '{name}' successfully.")
            return True
        except Exception as e:
            print(f"Registry Error: Exception registering tool '{name}': {e}")
            return False

    def unregister(self, name: str) -> bool:
        """Unregisters a tool, calling shutdown to cleanup resources."""
        if name in self._tools:
            try:
                self._tools[name].shutdown()
            except Exception as e:
                print(f"Registry Error: Error shutting down tool '{name}': {e}")
            del self._tools[name]
            print(f"Registry: Unregistered tool '{name}'.")
            return True
        return False

    def get_tool(self, name: str) -> Optional[IMCPServer]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_tool_by_capability(self, capability_name: str) -> Optional[IMCPServer]:
        """
        Scans all registered tools to find one that exposes the requested capability name.
        """
        for tool_name, tool_instance in self._tools.items():
            try:
                capabilities = tool_instance.discover_capabilities()
                if any(cap.name == capability_name for cap in capabilities):
                    return tool_instance
            except Exception as e:
                print(f"Registry Warning: Error scanning capabilities for tool '{tool_name}': {e}")
        return None
