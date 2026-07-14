from typing import List, Optional
from backend.llm.models.provider_registry import provider_registry, KeyInfo

def select_api_key(provider: str) -> Optional[KeyInfo]:
    """
    Selects the next API key based on the configured key rotation strategy.
    Strategies:
      - round_robin: sequentially select next healthy key
      - least_used: select healthy key with lowest success count
      - priority: select the first healthy key in the list (index order)
    """
    provider = provider.lower()
    
    # 1. Restore cooled off keys
    provider_registry.restore_unhealthy_keys()
    
    keys = provider_registry.get_keys(provider)
    if not keys:
        return None
        
    healthy_keys = [k for k in keys if k.is_healthy]
    
    # Fallback to all keys if everything is flagged unhealthy
    candidates = healthy_keys if healthy_keys else keys
    
    strategy = provider_registry.rotation_strategy.get(provider, "round_robin")
    
    if strategy == "least_used":
        # Sort by success count
        selected = min(candidates, key=lambda k: k.success_count)
        return selected
        
    elif strategy == "priority":
        # Simply return the first available (ordered by index)
        return candidates[0]
        
    else: # round_robin
        # Filter target indices in candidates
        current_idx = provider_registry._current_index.get(provider, 0)
        # Find next index in candidates list
        selected = candidates[current_idx % len(candidates)]
        provider_registry._current_index[provider] = (current_idx + 1) % len(candidates)
        return selected
