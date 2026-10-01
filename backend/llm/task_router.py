import os
import yaml
from typing import Dict, Any, Tuple

# Default fallback task configuration — chat on Groq (fast cloud, qwen fallback),
# all other tasks local-first (Ollama qwen3:8b)
DEFAULT_TASK_ROUTING = {
    "repository_summary": ("ollama", "qwen3:8b"),
    "chat": ("groq", "openai/gpt-oss-20b"),
    "code_review": ("ollama", "qwen3:8b"),
    "architecture_summary": ("ollama", "qwen3:8b"),
    "tool_selection": ("ollama", "qwen3:8b"),
    "offline": ("ollama", "qwen3:8b"),
    # Skills (README generator, utils.generate) use this task; pinned so it
    # never inherits chat's routing
    "analysis": ("ollama", "qwen3:8b")
}

class TaskRouter:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.rules: Dict[str, Tuple[str, str]] = {}
        self.load_rules()

    def load_rules(self):
        """Loads rules from model_config.yaml, falling back to defaults."""
        rules = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = yaml.safe_load(f)
                    if data and "tasks" in data:
                        for task, conf in data["tasks"].items():
                            rules[task] = (conf.get("provider", "groq"), conf.get("model", ""))
            except Exception as e:
                print(f"TaskRouter: Failed to load config from {self.config_path}: {e}")
        
        # Merge with defaults for missing keys
        for task, default in DEFAULT_TASK_ROUTING.items():
            if task not in rules or not rules[task][1]:
                rules[task] = default
                
        self.rules = rules

    def resolve_task(self, task: str) -> Tuple[str, str]:
        """Resolves task slug to (provider, model)."""
        return self.rules.get(task, self.rules.get("chat", ("ollama", "qwen3:8b")))

# Global instance pointing to default workspace location
config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "model_config.yaml"))
task_router = TaskRouter(config_file)
