
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

client = OpenAI(
    api_key=os.getenv("FREELLMAPI_API_KEY"),
    base_url=os.getenv("FREELLMAPI_BASE_URL"),
    timeout=60.0,
)

MODEL_NAME = "gemini-3.6-flash"

print(f"Testing model: {MODEL_NAME}")

try:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly this sentence: "
                           "FreeLLMAPI integration successful.",
            }
        ],
        max_tokens=150,
        temperature=0,
    )

    print("\n========== RESPONSE DIAGNOSTICS ==========")
    print("Model:", response.model)
    print("Response ID:", response.id)
    print("Finish reason:", response.choices[0].finish_reason)
    print("Content:", repr(response.choices[0].message.content))
    print("Usage:", response.usage)

except Exception as error:
    print("\nAPI TEST FAILED")
    print(type(error).__name__, str(error))
