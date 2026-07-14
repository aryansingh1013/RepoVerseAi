import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from backend.llm.providers.base_provider import BaseProvider, LLMResponse

class OllamaProvider(BaseProvider):
    def generate(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        json_mode: bool, 
        api_key: str, 
        endpoint: Optional[str] = None
    ) -> LLMResponse:
        start_time = time.time()
        base_url = endpoint if endpoint else "http://localhost:11434/v1"
        try:
            client = OpenAI(
                base_url=base_url,
                api_key="ollama" # placeholder
            )
            response_format = {"type": "json_object"} if json_mode else None
            
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
                timeout=25.0
            )
            
            latency = time.time() - start_time
            response_text = chat_completion.choices[0].message.content or ""
            tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0
            finish_reason = chat_completion.choices[0].finish_reason or "stop"
            
            # Ollama is local, so cost is 0!
            cost_estimate = 0.0
            
            return LLMResponse(
                provider="ollama",
                model=model,
                latency=latency,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                response=response_text,
                cost_estimate=cost_estimate,
                status="success"
            )
        except Exception as e:
            latency = time.time() - start_time
            return LLMResponse(
                provider="ollama",
                model=model,
                latency=latency,
                tokens_used=0,
                finish_reason="error",
                response="",
                cost_estimate=0.0,
                status="failed",
                error_message=str(e)
            )
