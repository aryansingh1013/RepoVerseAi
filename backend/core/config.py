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
    WORKSPACE_DIR: str = ""
    DB_DIR: str = ""
    
    def __init__(self, **values):
        super().__init__(**values)
        import json
        default_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        conf_path = os.path.join(os.path.dirname(__file__), "active_workspace.json")
        active_ws = None
        if os.path.exists(conf_path):
            try:
                with open(conf_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = data.get("active_workspace")
                    if val and os.path.exists(val):
                        active_ws = val
            except Exception:
                pass
        self.WORKSPACE_DIR = active_ws or default_root
        self.DB_DIR = os.path.join(default_root, "db")
    
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
    
    # Host configuration — 0.0.0.0 is required for Railway/cloud deployments
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.DB_DIR, exist_ok=True)
