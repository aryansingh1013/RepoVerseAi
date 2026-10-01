import os
from dotenv import load_dotenv

# Load env directly
load_dotenv(dotenv_path="c:/Users/Aryan Singh/OneDrive/Desktop/SUMMERTRAININGPROJECT/backend/.env", override=True)

from backend.llm.model_router import model_router
from backend.llm.models.provider_registry import provider_registry

def test():
    print("Starting test...")
    print(f"Groq keys loaded in registry: {provider_registry.get_keys('groq')}")
    print(f"OpenRouter keys loaded: {provider_registry.get_keys('openrouter')}")
    
    # Try a simple generation
    res = model_router.generate(
        task="chat",
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("---- Result ----")
    print(f"Status: {res.status}")
    print(f"Provider: {res.provider}")
    print(f"Error: {res.error_message}")
    
    # Print the fallback log
    print("---- Telemetry Log ----")
    for log in model_router.telemetry['fallback_chain_log']:
        print(log)

if __name__ == "__main__":
    test()
