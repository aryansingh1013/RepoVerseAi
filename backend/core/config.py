import os
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv

# Load backend/.env explicitly
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)


class Settings(BaseSettings):
    # App Paths
    WORKSPACE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DB_DIR: str = os.path.join(WORKSPACE_DIR, "db")
    
    # API Keys (Fallback to developer credentials if environment not set)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", "")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "")
    HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN", "")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY", "")
    
    # Models
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_MODEL_FALLBACK: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    PRIMARY_LLM: str = "llama-3.3-70b-versatile"
    SECONDARY_LLM: str = "Qwen/Qwen2.5-Coder-32B-Instruct"
    FALLBACK_LLM: str = "qwen2.5"  # Local Ollama model
    
    # Host configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.DB_DIR, exist_ok=True)
