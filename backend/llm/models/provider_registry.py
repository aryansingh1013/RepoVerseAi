import time
from typing import Dict, Any, List, Optional

class KeyInfo:
    def __init__(self, key: str, index: int):
        self.key = key
        self.alias = f"Key-{index + 1}"
        self.success_count = 0
        self.failure_count = 0
        self.rate_limit_count = 0
        self.last_failed_time = 0.0
        self.is_healthy = True

class ProviderRegistry:
    def __init__(self):
        self.keys: Dict[str, List[KeyInfo]] = {
            "groq": [],
            "openai": [],
            "huggingface": [],
            "gemini": [],
            "openrouter": []
        }
        self.ollama_endpoint = "http://localhost:11434/v1"
        self.rotation_strategy: Dict[str, str] = {
            "groq": "round_robin",
            "openai": "round_robin",
            "huggingface": "round_robin",
            "gemini": "round_robin",
            "openrouter": "round_robin"
        }
        self._current_index: Dict[str, int] = {
            "groq": 0,
            "openai": 0,
            "huggingface": 0,
            "gemini": 0,
            "openrouter": 0
        }

    def set_keys(self, provider: str, key_list: List[str]):
        """Sets keys for a provider and initializes metadata."""
        provider = provider.lower()
        if provider not in self.keys:
            return
        
        self.keys[provider] = [KeyInfo(k.strip(), idx) for idx, k in enumerate(key_list) if k.strip()]
        self._current_index[provider] = 0

    def get_keys(self, provider: str) -> List[KeyInfo]:
        return self.keys.get(provider.lower(), [])

    def mark_success(self, provider: str, key_alias: str):
        provider = provider.lower()
        for k in self.keys.get(provider, []):
            if k.alias == key_alias:
                k.success_count += 1
                k.is_healthy = True
                break

    def mark_failure(self, provider: str, key_alias: str, is_rate_limit: bool = False):
        provider = provider.lower()
        for k in self.keys.get(provider, []):
            if k.alias == key_alias:
                k.failure_count += 1
                k.last_failed_time = time.time()
                if is_rate_limit:
                    k.rate_limit_count += 1
                    k.is_healthy = False # Temporary block
                break

    def restore_unhealthy_keys(self):
        """Restores keys that have been cooling down for more than 60 seconds."""
        now = time.time()
        for provider, key_list in self.keys.items():
            for k in key_list:
                if not k.is_healthy and (now - k.last_failed_time > 60.0):
                    k.is_healthy = True

provider_registry = ProviderRegistry()
