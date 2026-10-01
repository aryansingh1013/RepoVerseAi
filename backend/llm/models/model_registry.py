from typing import Dict, Any, List

# Standard registry of models supported by RepoVerse
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Groq models (llama-3.3-70b-versatile / llama-3.1-8b-instant moved to
    # Enterprise-only in Aug 2026 — replaced with current production models)
    "openai/gpt-oss-120b": {
        "provider": "groq",
        "description": "GPT-OSS 120B on Groq (production)",
        "input_cost_per_1m": 0.15,
        "output_cost_per_1m": 0.60
    },
    "openai/gpt-oss-20b": {
        "provider": "groq",
        "description": "GPT-OSS 20B on Groq (production, fast)",
        "input_cost_per_1m": 0.075,
        "output_cost_per_1m": 0.30
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
    
    # Gemini models (gemini-1.5-flash retired — current GA model)
    "gemini-2.0-flash": {
        "provider": "gemini",
        "description": "Gemini 2.0 Flash",
        "input_cost_per_1m": 0.10,
        "output_cost_per_1m": 0.40
    },
    
    # Ollama models
    "qwen3:8b": {
        "provider": "ollama",
        "description": "Local Qwen3 8B (thinking model, primary)",
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0
    },
    "qwen2.5": {
        "provider": "ollama",
        "description": "Local Qwen 2.5 Coder",
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0
    }
}
