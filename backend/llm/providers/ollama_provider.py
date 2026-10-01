import re
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from backend.llm.providers.base_provider import BaseProvider, LLMResponse


def _ollama_timeout() -> float:
    """Configurable generation timeout for local inference.
    qwen3:8b on CPU needs minutes for structured JSON; a short timeout caused
    premature failover to cloud providers (local-first policy violation)."""
    import os
    try:
        return float(os.getenv("OLLAMA_TIMEOUT", "600"))
    except (TypeError, ValueError):
        return 600.0


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
            
            # Local models (e.g. qwen3:8b) think before answering; budget
            # generously so the answer itself is not truncated. Thinking
            # blocks are stripped below. Timeout is configurable via
            # OLLAMA_TIMEOUT (default 600s) for CPU-class hardware.
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                response_format=response_format,
                max_tokens=4096,
                timeout=_ollama_timeout()
            )
            
            latency = time.time() - start_time
            response_text = chat_completion.choices[0].message.content or ""
            tokens_used = chat_completion.usage.total_tokens if chat_completion.usage else 0
            finish_reason = chat_completion.choices[0].finish_reason or "stop"

            # Strip Qwen3-style thinking blocks (<think>...</think>) so agent
            # parsing/verification never sees them. Handles multi-line blocks.
            response_text = re.sub(
                r"<think>.*?</think>", "", response_text, flags=re.DOTALL
            ).strip()
            # An unterminated <think> (generation cut) must not leak either.
            if response_text.startswith("<think>") and "</think>" not in response_text:
                response_text = ""
            
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
