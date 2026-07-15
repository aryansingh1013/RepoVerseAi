import os
import sys

# Add backend directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

import uvicorn
from backend.app import app

if __name__ == "__main__":
    # Hugging Face Gradio spaces expect the app on port 7860
    port = int(os.getenv("PORT", 7860))
    print(f"Starting RepoVerse AI on port {port}...")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=False)
