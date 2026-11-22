
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# -----------------------------------------
# PRIMARY PROVIDER: FreeLLMAPI
# -----------------------------------------

FREELLMAPI_API_KEY = os.getenv("FREELLMAPI_API_KEY")
FREELLMAPI_BASE_URL = os.getenv(
    "FREELLMAPI_BASE_URL",
    "http://127.0.0.1:31415/v1",
)

FREELLMAPI_MODEL = "gemini-3.6-flash"

free_llm_client = None

if FREELLMAPI_API_KEY:
    free_llm_client = OpenAI(
        api_key=FREELLMAPI_API_KEY,
        base_url=FREELLMAPI_BASE_URL,
        timeout=60.0,
    )


# -----------------------------------------
# SECONDARY PROVIDER: Direct Gemini
# -----------------------------------------

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash"

gemini_client = None

if GOOGLE_API_KEY:
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)


# -----------------------------------------
# MAIN LLM FUNCTION
# -----------------------------------------

def generate_response(prompt: str) -> str:
    """
    Generate an AI response.

    Primary: FreeLLMAPI
    Fallback: Direct Gemini API

    Keeps the same function interface used by
    the existing LangGraph analysis node.
    """

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    errors = []

    # Try FreeLLMAPI first.
    if free_llm_client is not None:
        try:
            response = free_llm_client.chat.completions.create(
                model=FREELLMAPI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=1500,
                temperature=0,
            )

            content = response.choices[0].message.content

            if isinstance(content, str) and content.strip():
                print("[LLM] Response generated using FreeLLMAPI.")
                return content.strip()

            errors.append("FreeLLMAPI returned empty content.")

        except Exception as error:
            errors.append(f"FreeLLMAPI failed: {error}")
            print(
                f"[LLM] FreeLLMAPI error: "
                f"{type(error).__name__}: {error}"
            )
            print("[LLM] Trying Gemini fallback.")

    else:
        errors.append("FreeLLMAPI API key is missing.")

    # Try direct Gemini as fallback.
    if gemini_client is not None:
        try:
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )

            content = response.text

            if isinstance(content, str) and content.strip():
                print("[LLM] Response generated using direct Gemini.")
                return content.strip()

            errors.append("Gemini returned empty content.")

        except Exception as error:
            errors.append(f"Direct Gemini failed: {error}")

    else:
        errors.append("Google API key is missing.")

    raise RuntimeError(
        "All configured LLM providers failed:\n"
        + "\n".join(errors)
    )
