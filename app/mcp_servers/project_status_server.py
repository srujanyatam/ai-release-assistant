
from mcp.server.fastmcp import FastMCP

# Create our MCP server
mcp = FastMCP("AI Release Assistant")


@mcp.tool()
def get_project_status() -> dict:
    """
    Get the current development status of the AI Release Assistant project.
    """
    return {
        "project": "AI Release Assistant",
        "current_day": 1,
        "status": "MCP fundamentals",
        "completed": [
            "Python environment setup",
            "Git repository initialization",
            "GitHub repository creation",
        ],
        "next_steps": [
            "Build GitHub MCP tools",
            "Build operations MCP tools",
            "Create LangGraph agent",
        ],
    }

@mcp.tool()
def check_component_status(component: str) -> dict:
    """
    Check the development status of an AI Release Assistant component.
    """

    components = {
        "github_mcp": "Planned",
        "ops_mcp": "Planned",
        "langgraph_agent": "Planned",
        "fastapi": "Planned",
        "evaluation": "Planned",
    }

    component = component.lower().strip()

    if component not in components:
        return {
            "component": component,
            "error": "Unknown component",
            "available_components": list(components.keys()),
        }

    return {
        "component": component,
        "status": components[component],
    }



if __name__ == "__main__":
    mcp.run()
