from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class LLMResponse(BaseModel):
    provider: str
    model: str
    latency: float
    tokens_used: int
    finish_reason: str
    response: str
    cost_estimate: float
    status: str
    error_message: Optional[str] = None

class BaseProvider(ABC):
    @abstractmethod
    def generate(
        self, 
        model: str, 
        messages: List[Dict[str, str]], 
        temperature: float, 
        json_mode: bool, 
        api_key: str, 
        endpoint: Optional[str] = None
    ) -> LLMResponse:
        """
        Executes a chat completion query and returns standard LLMResponse.
        """
        pass
