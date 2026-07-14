from typing import List, Dict, Any, Optional
from backend.llm.providers.base_provider import BaseProvider, LLMResponse
from backend.llm.providers.openai_provider import OpenAIProvider
from backend.llm.providers.groq_provider import GroqProvider
from backend.llm.providers.huggingface_provider import HuggingFaceProvider
from backend.llm.providers.gemini_provider import GeminiProvider
from backend.llm.providers.openrouter_provider import OpenRouterProvider
from backend.llm.providers.ollama_provider import OllamaProvider

class ProviderRouter:
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {
            "openai": OpenAIProvider(),
            "groq": GroqProvider(),
            "huggingface": HuggingFaceProvider(),
            "gemini": GeminiProvider(),
            "openrouter": OpenRouterProvider(),
            "ollama": OllamaProvider()
        }

    def generate(
        self, 
        provider: str,
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        json_mode: bool, 
        api_key: str, 
        endpoint: Optional[str] = None
    ) -> LLMResponse:
        provider = provider.lower()
        executor = self.providers.get(provider)
        if not executor:
            raise ValueError(f"ProviderRouter: Unsupported provider '{provider}' requested!")
            
        return executor.generate(
            model=model,
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            api_key=api_key,
            endpoint=endpoint
        )

provider_router = ProviderRouter()
