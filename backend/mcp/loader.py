import os
import sys
import importlib.util
import inspect
from typing import List
from backend.mcp.interfaces import IMCPServer
from backend.mcp.registry import MCPServerRegistry

class DynamicToolLoader:
    def __init__(self, registry: MCPServerRegistry, plugins_dir: str = None):
        self.registry = registry
        # Default plugins folder in project root backend/plugins
        if plugins_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.plugins_dir = os.path.join(project_root, "backend", "plugins")
        else:
            self.plugins_dir = os.path.abspath(plugins_dir)

    def load_plugins(self) -> List[str]:
        """
        Scans plugins_dir for modules starting with 'mcp_' and registers classes
        that implement IMCPServer.
        """
        loaded_names = []
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            print(f"Loader: Created plugins directory at {self.plugins_dir}")
            return loaded_names

        sys.path.append(self.plugins_dir)

        for file in os.listdir(self.plugins_dir):
            if file.startswith("mcp_") and file.endswith(".py"):
                module_name = file[:-3] # Remove .py extension
                file_path = os.path.join(self.plugins_dir, file)

                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                        # Inspect classes in module
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (
                                inspect.isclass(attr) 
                                and issubclass(attr, IMCPServer) 
                                and attr is not IMCPServer
                                and attr.__module__ == module_name
                            ):
                                # Instantiate and register
                                server_instance = attr()
                                # Use class name or standard property if available as slug
                                slug_name = getattr(server_instance, "name", attr_name.lower())
                                success = self.registry.register(slug_name, server_instance)
                                if success:
                                    loaded_names.append(slug_name)
                                    print(f"Loader: Dynamically loaded plugin class '{attr_name}' as '{slug_name}'")
                except Exception as e:
                    print(f"Loader Error: Failed to load plugin file '{file}': {e}")

        return loaded_names
