# AI Release Assistant

An AI-powered CI/CD release assistant built with Python, MCP (Model Context Protocol), and LangGraph.

The goal is to build an intelligent system that investigates failed CI/CD workflows, identifies probable root causes, recommends corrective actions, and executes approved operations with human oversight.

## Project Goals

- Integrate with GitHub Actions to retrieve workflow runs and failure logs.
- Use MCP servers to expose GitHub and operations tools.
- Use LangGraph to orchestrate an AI-powered investigation workflow.
- Analyse build failures and identify probable root causes.
- Recommend fixes, workflow reruns, or rollback actions.
- Require human approval before executing sensitive operations.
- Maintain an audit log of agent decisions and tool executions.
- Evaluate root-cause accuracy using intentionally broken commits.

## Planned Technology Stack

- Python 3.12
- MCP Python SDK
- LangGraph
- Claude or Gemini API
- FastAPI
- GitHub Actions
- Docker
- Pytest

## Architecture

```text
GitHub Actions
      |
      v
Failed Workflow Webhook
      |
      v
FastAPI Service
      |
      v
LangGraph Agent
      |
      +------ GitHub MCP Server
      |
      +------ Operations MCP Server
      |
      v
Root Cause Analysis
      |
      v
Human Approval
      |
      v
Approved Action Execution
      |
      v
Audit Log
```

## Development Status

Currently under development.

The architecture and integrations will be implemented incrementally. Simulated operations will be clearly distinguished from real GitHub integrations.

## Safety

Sensitive operations such as rollback will require explicit human approval. The agent will not independently execute destructive actions.

## License

Not yet selected.