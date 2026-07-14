from typing import Dict, Any, List

# Standard registry of models supported by RepoVerse
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Groq models
    "llama-3.3-70b-versatile": {
        "provider": "groq",
        "description": "Llama 3.3 70B Versatile",
        "input_cost_per_1m": 0.05,
        "output_cost_per_1m": 0.08
    },
    "llama-3.1-8b-instant": {
        "provider": "groq",
        "description": "Llama 3.1 8B Instant",
        "input_cost_per_1m": 0.05,
        "output_cost_per_1m": 0.05
    },
    
    # OpenAI models
    "gpt-4o-mini": {
        "provider": "openai",
        "description": "GPT-4o Mini (Fast & Cheap)",
        "input_cost_per_1m": 0.15,
        "output_cost_per_1m": 0.60
    },
    "gpt-4o": {
        "provider": "openai",
        "description": "GPT-4o (Reasoning & High Quality)",
        "input_cost_per_1m": 5.0,
        "output_cost_per_1m": 15.0
    },
    
    # HuggingFace models
    "Qwen/Qwen2.5-Coder-7B-Instruct": {
        "provider": "huggingface",
        "description": "Qwen 2.5 Coder 7B",
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0
    },
    
    # Gemini models
    "gemini-1.5-flash": {
        "provider": "gemini",
        "description": "Gemini 1.5 Flash",
        "input_cost_per_1m": 0.075,
        "output_cost_per_1m": 0.30
    },
    
    # Ollama models
    "qwen2.5": {
        "provider": "ollama",
        "description": "Local Qwen 2.5 Coder",
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0
    }
}
