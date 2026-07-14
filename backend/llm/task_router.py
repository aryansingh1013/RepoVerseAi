import os
import yaml
from typing import Dict, Any, Tuple

# Default fallback task configuration
DEFAULT_TASK_ROUTING = {
    "repository_summary": ("huggingface", "Qwen/Qwen2.5-Coder-7B-Instruct"),
    "chat": ("groq", "llama-3.3-70b-versatile"),
    "code_review": ("huggingface", "Qwen/Qwen2.5-Coder-7B-Instruct"),
    "architecture_summary": ("huggingface", "Qwen/Qwen2.5-Coder-7B-Instruct"),
    "tool_selection": ("groq", "llama-3.3-70b-versatile"),
    "offline": ("ollama", "qwen2.5")
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
        return self.rules.get(task, self.rules.get("chat", ("groq", "llama-3.3-70b-versatile")))

# Global instance pointing to default workspace location
config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "model_config.yaml"))
task_router = TaskRouter(config_file)
