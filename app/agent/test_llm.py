import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / '.env')

api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    raise RuntimeError('GOOGLE_API_KEY is missing from .env')

def main():
    print('Connecting to Gemini...')

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents='Reply with exactly: AI Release Assistant Gemini connection successful.'
    )

    print('\nGemini response:')
    print(response.text)
    print('\nGemini connection test: SUCCESS')

if __name__ == '__main__':
    main()
