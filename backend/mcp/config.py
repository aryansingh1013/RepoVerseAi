import os
import json
from typing import Dict, Any

SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "mcp_settings.json"
)

DEFAULT_SETTINGS = {
    "github_token": os.environ.get("GITHUB_TOKEN", ""),
    "filesystem_root": os.environ.get("WORKSPACE_DIR", "c:\\Users\\Aryan Singh\\OneDrive\\Desktop\\SUMMERTRAININGPROJECT"),
    "terminal_safe_mode": True,
    "connection_timeout": 30,
    "refresh_interval": 60
}

class MCPSettingsManager:
    def __init__(self):
        self.settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except Exception as e:
                print(f"MCPSettings Error: Failed to load settings from file: {e}")

    def save(self, new_data: Dict[str, Any]):
        self.settings.update(new_data)
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
            print(f"MCPSettings: Saved config parameters successfully to {SETTINGS_FILE}")
        except Exception as e:
            print(f"MCPSettings Error: Failed to save settings to file: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

mcp_settings = MCPSettingsManager()
