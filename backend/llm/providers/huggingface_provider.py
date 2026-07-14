import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from backend.llm.providers.base_provider import BaseProvider, LLMResponse

class HuggingFaceProvider(BaseProvider):
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
            # Hugging Face Serverless Inference OpenAI compatible API base
            client = OpenAI(
                base_url="https://api-inference.huggingface.co/v1",
                api_key=api_key
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
            
            # HuggingFace Serverless inference is generally free / low tier
            cost_estimate = 0.0
            
            return LLMResponse(
                provider="huggingface",
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
                provider="huggingface",
                model=model,
                latency=latency,
                tokens_used=0,
                finish_reason="error",
                response="",
                cost_estimate=0.0,
                status="failed",
                error_message=str(e)
            )
