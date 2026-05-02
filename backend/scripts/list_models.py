import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import google.generativeai as genai

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "env.txt")
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GEMINI_API"))
if not api_key:
    print("No API key found")
    sys.exit(1)

genai.configure(api_key=api_key)

try:
    for m in genai.list_models():
        print(m.name)
except Exception as e:
    print("Error:", e)
