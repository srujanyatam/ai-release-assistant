
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("FREELLMAPI_API_KEY")
BASE_URL = os.getenv(
    "FREELLMAPI_BASE_URL",
    "http://127.0.0.1:31415/v1",
)

if not API_KEY:
    raise RuntimeError("FREELLMAPI_API_KEY is missing from .env")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=30.0,
)

print("Connecting to FreeLLMAPI...")

try:
    models = client.models.list()

    print("\nConnection successful!")
    print(f"Models returned: {len(models.data)}")

    print("\nAvailable model IDs:")
    for model in models.data:
        print(f"- {model.id}")

    print("\nFreeLLMAPI connection test: SUCCESS")

except Exception as error:
    print("\nFreeLLMAPI connection test: FAILED")
    print(f"Error: {error}")
