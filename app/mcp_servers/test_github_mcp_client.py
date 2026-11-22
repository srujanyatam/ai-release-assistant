
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


async def main():
    client = MultiServerMCPClient(
        {
            "github": {
                "transport": "stdio",
                "command": sys.executable,
                "args": [
                    str(
                        PROJECT_ROOT
                        / "app"
                        / "mcp_servers"
                        / "github_server.py"
                    )
                ],
                "env": os.environ.copy(),
            }
        }
    )

    tools = await client.get_tools()

    logs_tool = next(
        (tool for tool in tools if tool.name == "get_run_logs"),
        None,
    )

    if logs_tool is None:
        raise RuntimeError("get_run_logs tool was not found.")

    print("Calling GitHub MCP get_run_logs tool...")

    # This is deliberately a fake run ID.
    # It tests tool invocation without changing anything.
    result = await logs_tool.ainvoke({"run_id": 12345})

    print("\nTool response:")
    print(result)

    print("\nLog-fetching MCP tool invocation completed.")


if __name__ == "__main__":
    asyncio.run(main())
