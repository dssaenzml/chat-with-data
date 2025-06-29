# Chat with Data - Backend

This is the FastAPI backend for the Chat with Data platform, featuring LangGraph orchestration and CrewAI multi-agent collaboration.

## Documentation

For complete setup, usage, and deployment instructions, please see the main [README.md](../README.md) in the project root.

## Quick Start

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Features

- **LangGraph Workflow Orchestration** - Intelligent query routing and processing
- **CrewAI Multi-Agent System** - Collaborative data analysis with specialized agents
- **Vector Search** - Qdrant integration for semantic search
- **LLM Observability** - Langfuse integration for tracking and analytics
- **Multiple Data Sources** - Support for files, databases, and APIs

## Architecture

This backend serves as the orchestration layer, coordinating between:
- LangGraph workflow management
- CrewAI agent collaboration
- Database and vector search services
- LLM providers (OpenAI, Anthropic)
- Langfuse observability platform 