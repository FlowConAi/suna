# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in the Suna backend repository.

## Project Overview

Suna is an open-source generalist AI agent that helps users accomplish real-world tasks with natural conversation. The backend is responsible for handling API requests, managing agent execution, processing LLM responses, and orchestrating tool execution.

## Architecture

The backend consists of the following major components:

1. **API Layer (api.py)**: FastAPI-based REST API that handles client requests, authentication, and streaming responses.

2. **Agent System**:
   - **ThreadManager**: Manages conversation threads, contexts, and interactions with the LLM.
   - **ResponseProcessor**: Processes LLM responses, identifies tool calls, and manages streaming.
   - **ToolRegistry**: Registers and manages available tools and their schemas.
   - **ContextManager**: Manages context window size through token counting and summarization.

3. **Tools System**:
   - **Tool (abstract class)**: Base class for all tools with schema registration support.
   - **Concrete Tools**: Various implementations like browser automation, file management, etc.
   - **Tool Schemas**: OpenAPI and XML-based schemas for tool definitions.

4. **Sandbox System**:
   - **Daytona Integration**: For isolated execution environments.
   - **Sandbox Management**: Creating, accessing, and cleaning up sandboxes.

5. **Services**:
   - **LLM Service**: Unified interface for various LLM providers via LiteLLM.
   - **Supabase Service**: Database access layer for persistent storage.
   - **Redis Service**: State management, message streaming, and coordination.
   - **Billing Service**: Usage tracking and subscription management.
   - **Langfuse Integration**: Observability and analytics for LLM calls.

## Key Files and Directories

- `api.py`: Main FastAPI application with endpoints and lifecycle management.
- `run_agent_background.py`: Background task worker for agent execution.
- `agent/`:
  - `api.py`: API endpoints specific to agent execution.
  - `run.py`: Core agent execution logic.
  - `prompt.py`: System prompts and instructions for the agent.
  - `tools/`: Directory containing all tool implementations.
- `agentpress/`:
  - `thread_manager.py`: Thread and conversation management.
  - `tool_registry.py`: Tool registration and discovery.
  - `response_processor.py`: LLM response processing and tool execution.
  - `context_manager.py`: Context window management and summarization.
  - `tool.py`: Base Tool class and schema decorators.
- `sandbox/`: Sandbox environment management.
- `services/`:
  - `llm.py`: LLM integration via LiteLLM.
  - `supabase.py`: Database access layer.
  - `redis.py`: Redis integration for state management.
  - `billing.py`: Subscription and usage tracking.
  - `langfuse_integration.py`: LLM observability and metrics.
- `utils/`: Utility functions and helpers.

## Development Commands

```bash
# Navigate to backend directory
cd backend

# Install dependencies
poetry install

# Run Redis and RabbitMQ (required for backend)
docker compose up redis rabbitmq -d

# Run API server (in one terminal)
poetry run python3.11 api.py

# Run worker (in another terminal)
poetry run python3.11 -m dramatiq run_agent_background

# Run tests
poetry run pytest
```

## API Endpoints Overview

- `/api/health`: Health check endpoint
- `/api/thread/{thread_id}/agent/start`: Start agent execution
- `/api/agent-run/{agent_run_id}`: Get agent run status
- `/api/agent-run/{agent_run_id}/stream`: Stream agent responses
- `/api/agent-run/{agent_run_id}/stop`: Stop agent execution
- `/api/thread/{thread_id}/agent-runs`: List agent runs for a thread
- `/api/agent/initiate`: Initialize agent with files

## Development Workflows

### Adding a New Tool

1. Create a new tool class that inherits from `Tool` in `agent/tools/`
2. Implement required methods with appropriate decorators:
   - Use `@openapi_schema` for function-style tools
   - Use `@xml_schema` for XML-based tools
3. Register tool in `agent/run.py` via `thread_manager.register_tool()`
4. Add tool description to system prompt if necessary

### Modifying LLM Integration

1. Update `services/llm.py` for LLM-specific changes
2. Use `prepare_params()` function to adjust parameters for specific models
3. Enable observability by configuring Langfuse in `.env`

### Context Management

1. Token counting and summarization logic is in `agentpress/context_manager.py`
2. Thread message management happens in `agentpress/thread_manager.py`
3. Message retrieval with summaries is handled by `services/supabase.py`

## Environment Configuration

The backend uses environment variables for configuration. Create a `.env` file based on `.env.example` with:

```
# Environment
ENV_MODE=local

# Database
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Redis
REDIS_HOST=localhost  # Use 'redis' for Docker-to-Docker
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_SSL=false

# RabbitMQ
RABBITMQ_HOST=localhost  # Use 'rabbitmq' for Docker-to-Docker
RABBITMQ_PORT=5672

# LLM Providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
MODEL_TO_USE=anthropic/claude-3-7-sonnet-latest

# Observability
LANGFUSE_ENABLED=false
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com

# Web Search
TAVILY_API_KEY=
FIRECRAWL_API_KEY=
FIRECRAWL_URL=https://api.firecrawl.dev

# Sandbox
DAYTONA_API_KEY=
DAYTONA_SERVER_URL=https://app.daytona.io/api
DAYTONA_TARGET=us
```

## Debugging Tips

1. **LLM API Issues**: Check `services/llm.py` logs for details about API failures
2. **Tool Execution Errors**: Look for errors in the `run_agent_background.py` logs
3. **Database Connection Problems**: Verify Supabase credentials and ensure tables exist
4. **Redis Connection Issues**: Check if Redis is running and accessible
5. **Sandbox Problems**: Verify Daytona API key and service status
6. **Response Processing Errors**: Look at `response_processor.py` for parsing issues

## Performance Considerations

1. Use connection pooling for Supabase when possible
2. Be mindful of token usage with large context windows
3. Implement proper caching strategies for repeated requests
4. Consider rate limiting for external API calls
5. Use streaming responses for better user experience

## Security Guidelines

1. Always validate and sanitize user inputs
2. Use proper authentication checks on all endpoints
3. Keep API keys secure and never commit them
4. Sandbox all user-generated code execution
5. Implement proper error handling without exposing sensitive information