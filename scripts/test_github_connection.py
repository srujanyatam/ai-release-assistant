
import os
import httpx
from dotenv import load_dotenv

# Load environment variables from the project root
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")

# Validate configuration before making a request
if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
    raise ValueError(
        "Missing GitHub configuration. Check your .env file."
    )

# GitHub API request headers
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "AI-Release-Assistant",
}

# Repository API endpoint
url = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}"
)

def test_github_connection():
    try:
        with httpx.Client(
            headers=headers,
            timeout=15.0
        ) as client:

            response = client.get(url)
            response.raise_for_status()

            repository = response.json()

            print("\nGitHub connection successful!")
            print("--------------------------------")
            print("Repository:", repository["full_name"])
            print("Visibility:", repository["visibility"])
            print("Default branch:", repository["default_branch"])
            print("Repository URL:", repository["html_url"])

    except httpx.HTTPStatusError as error:
        print("GitHub API returned an error.")
        print("HTTP status:", error.response.status_code)
        print("Response:", error.response.text)

    except httpx.RequestError as error:
        print("Could not connect to GitHub.")
        print("Reason:", str(error))


if __name__ == "__main__":
    test_github_connection()
