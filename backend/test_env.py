import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="c:/Users/Aryan Singh/OneDrive/Desktop/SUMMERTRAININGPROJECT/backend/.env", override=True)

print("--- ENV FILE LOADED ---")
print(f"GROQ_API_KEY: {repr(os.environ.get('GROQ_API_KEY'))}")
print(f"GEMINI_API_KEY: {repr(os.environ.get('GEMINI_API_KEY'))}")
