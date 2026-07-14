import os
import time
import yaml
from typing import List, Dict, Any, Optional, Tuple
from backend.llm.providers.base_provider import LLMResponse
from backend.llm.task_router import task_router
from backend.llm.provider_router import provider_router
from backend.llm.models.provider_registry import provider_registry, KeyInfo
from backend.llm.models.routing_rules import select_api_key
from backend.llm.models.model_registry import MODEL_REGISTRY

# Default configuration parameters
DEFAULT_FALLBACK_ORDER = ["groq", "openrouter", "openai", "gemini", "ollama"]

class ModelRouter:
    def __init__(self, provider_config_path: str):
        self.provider_config_path = provider_config_path
        self.fallback_order = DEFAULT_FALLBACK_ORDER.copy()
        
        # Telemetry logs
        self.telemetry = {
            "requests_total": 0,
            "failures_total": 0,
            "rate_limits_total": 0,
            "fallback_events_total": 0,
            "latency_sum": 0.0,
            "latency_count": 0,
            "fallback_chain_log": []
        }
        
        self.load_provider_config()

    def load_provider_config(self):
        """Loads provider keys and settings from provider_config.yaml."""
        if os.path.exists(self.provider_config_path):
            try:
                with open(self.provider_config_path, "r") as f:
                    data = yaml.safe_load(f)
                    if data and "providers" in data:
                        for prov, conf in data["providers"].items():
                            prov = prov.lower()
                            # Load keys
                            keys = conf.get("keys", [])
                            if keys:
                                provider_registry.set_keys(prov, keys)
                            
                            # Load rotation strategy
                            strategy = conf.get("preferred_key_selection", "round_robin")
                            provider_registry.rotation_strategy[prov] = strategy
                            
                            # Load Ollama endpoint
                            if prov == "ollama" and "endpoint" in conf:
                                provider_registry.ollama_endpoint = conf["endpoint"]
                                
                    if data and "fallback_order" in data:
                        self.fallback_order = data["fallback_order"]
            except Exception as e:
                print(f"ModelRouter: Failed to load provider config from {self.provider_config_path}: {e}")

        # Inject environment variable keys as defaults loaded from settings/env
        from backend.core.config import settings
        env_keys = {
            "groq": settings.GROQ_API_KEY,
            "openai": settings.OPENAI_API_KEY,
            "huggingface": settings.HF_TOKEN,
            "gemini": settings.GEMINI_API_KEY,
            "openrouter": settings.OPENROUTER_API_KEY
        }
        for prov, val in env_keys.items():
            if val:
                keys_list = [k.strip() for k in val.split(",") if k.strip()]
                provider_registry.set_keys(prov, keys_list)
            else:
                provider_registry.set_keys(prov, []) # Clear if not present in env

    def generate(
        self,
        task: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Standardized entry gate for all LLM calls. Handles key rotation, fallback chain retries, 
        and updates performance telemetry.
        """
        # 1. Resolve starting provider/model for the task
        start_provider, start_model = task_router.resolve_task(task)
        
        # 2. Build full fallback sequence
        provider_fallback_chain = []
        if start_provider in self.fallback_order:
            idx = self.fallback_order.index(start_provider)
            # Start at primary, fallback down the list
            provider_fallback_chain = self.fallback_order[idx:] + self.fallback_order[:idx]
        else:
            provider_fallback_chain = [start_provider] + self.fallback_order
            
        # De-duplicate fallback chain
        provider_fallback_chain = list(dict.fromkeys(provider_fallback_chain))

        last_error = "No provider attempted"
        
        # Try each provider in fallback sequence
        for current_provider in provider_fallback_chain:
            # Match target model for provider
            current_model = start_model
            if current_provider != start_provider:
                # Find first model registered in registry for this provider
                matches = [m for m, spec in MODEL_REGISTRY.items() if spec["provider"] == current_provider]
                current_model = matches[0] if matches else "default"
            
            # Resolve Ollama specific names
            if current_provider == "ollama" and current_model == "default":
                current_model = "qwen2.5"

            # Determine endpoint if Ollama
            endpoint = None
            if current_provider == "ollama":
                endpoint = provider_registry.ollama_endpoint

            # Resolve keys
            keys = provider_registry.get_keys(current_provider)
            
            # If a provider requires credentials but has no keys registered, skip it!
            if current_provider not in ["ollama"] and not keys:
                continue
                
            # If Ollama or no keys required, run single attempt with placeholder key
            attempts = len(keys) if keys else 1
            
            for _ in range(attempts):
                # Select next key
                key_info = select_api_key(current_provider)
                api_key = key_info.key if key_info else "placeholder"
                key_alias = key_info.alias if key_info else "env_or_default"

                self.telemetry["requests_total"] += 1
                
                # Execute completion call
                res = provider_router.generate(
                    provider=current_provider,
                    model=current_model,
                    messages=messages,
                    temperature=temperature,
                    json_mode=json_mode,
                    api_key=api_key,
                    endpoint=endpoint
                )
                
                if res.status == "success":
                    # Record telemetry metrics
                    self.telemetry["latency_sum"] += res.latency
                    self.telemetry["latency_count"] += 1
                    if key_info:
                        provider_registry.mark_success(current_provider, key_alias)
                    return res
                else:
                    # Mark failure and retry key or fallback
                    self.telemetry["failures_total"] += 1
                    err_msg = res.error_message or "Unknown provider failure"
                    last_error = err_msg
                    
                    is_rate_limit = "429" in err_msg or "rate limit" in err_msg.lower()
                    if is_rate_limit:
                        self.telemetry["rate_limits_total"] += 1
                        
                    if key_info:
                        provider_registry.mark_failure(current_provider, key_alias, is_rate_limit)
                    
                    log_entry = f"Failure: provider={current_provider}, key={key_alias}, error={err_msg}"
                    self.telemetry["fallback_chain_log"].append(log_entry)
                    print(f"ModelRouter: Attempt failed. {log_entry}")

            # All keys failed for this provider, trigger provider fallback event
            self.telemetry["fallback_events_total"] += 1
            fallback_log = f"Provider '{current_provider}' exhausted. Falling back to next provider in sequence."
            self.telemetry["fallback_chain_log"].append(fallback_log)
            print(f"ModelRouter: {fallback_log}")

        # If we got here, all providers failed
        return LLMResponse(
            provider="failed",
            model="none",
            latency=0.0,
            tokens_used=0,
            finish_reason="exhausted",
            response=f"Error: All LLM providers in the fallback chain were exhausted. Last error: {last_error}",
            cost_estimate=0.0,
            status="failed",
            error_message=last_error
        )

# Global ModelRouter instance
provider_config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "provider_config.yaml"))
model_router = ModelRouter(provider_config_file)
