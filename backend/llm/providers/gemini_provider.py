import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from backend.llm.providers.base_provider import BaseProvider, LLMResponse

class GeminiProvider(BaseProvider):
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
        try:
            # Gemini OpenAI-compatible API base
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=api_key
            )
            response_format = {"type": "json_object"} if json_mode else None
            
            # Map default model name to gemini name if needed
            gemini_model = model
            if "gemini" not in model.lower():
                gemini_model = "gemini-1.5-flash"
                
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=gemini_model,
                temperature=temperature,
                response_format=response_format,
                timeout=25.0
            )
            
            latency = time.time() - start_time
            response_text = chat_completion.choices[0].message.content or ""
            tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0
            finish_reason = chat_completion.choices[0].finish_reason or "stop"
            
            # Approximate Gemini 1.5 Flash cost: $0.075 / 1M tokens
            cost_estimate = (tokens_used / 1_000_000) * 0.075
            
            return LLMResponse(
                provider="gemini",
                model=gemini_model,
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
                provider="gemini",
                model=model,
                latency=latency,
                tokens_used=0,
                finish_reason="error",
                response="",
                cost_estimate=0.0,
                status="failed",
                error_message=str(e)
            )
