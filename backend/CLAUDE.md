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

### Core Endpoints

- **Health Check**: `GET /api/health`
  - Returns API status and maintenance information
  - No authentication required

- **Agent Execution**: 
  - `POST /api/thread/{thread_id}/agent/start` - Start agent execution
  - `GET /api/agent-run/{agent_run_id}` - Get agent run status
  - `GET /api/agent-run/{agent_run_id}/stream` - Stream responses via SSE
  - `POST /api/agent-run/{agent_run_id}/stop` - Stop agent execution
  - `GET /api/thread/{thread_id}/agent-runs` - List runs for thread

- **File Management**:
  - `POST /api/agent/initiate` - Initialize agent with uploaded files
  - Returns thread_id for created conversation

### Authentication

All endpoints except `/health` require JWT authentication:
```python
user_id = Depends(get_current_user_id_from_jwt)
```

For SSE endpoints, token passed as query parameter:
```
/api/agent-run/{id}/stream?token=<jwt_token>
```

## Development Workflows

### Adding a New Tool

1. **Create Tool Class** in `agent/tools/`:
   ```python
   from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema
   
   class MyNewTool(Tool):
       def __init__(self, project_id: str = None):
           super().__init__()
           self.project_id = project_id
   ```

2. **Implement Tool Methods** with schema decorators:
   ```python
   @openapi_schema({
       "type": "function",
       "function": {
           "name": "my_function",
           "description": "What this function does",
           "parameters": {
               "type": "object",
               "properties": {
                   "param1": {"type": "string", "description": "Parameter description"}
               },
               "required": ["param1"]
           }
       }
   })
   async def my_function(self, param1: str) -> ToolResult:
       try:
           # Implementation
           return self.success_response(result)
       except Exception as e:
           return self.fail_response(f"Error: {str(e)}")
   ```

3. **For Sandbox Tools**, inherit from `SandboxToolsBase`:
   ```python
   from sandbox.tool_base import SandboxToolsBase
   
   class MySandboxTool(SandboxToolsBase):
       async def my_sandbox_function(self, file_path: str) -> ToolResult:
           sandbox = await self._ensure_sandbox()
           clean_path = self._clean_path(file_path)  # Auto-prefixes /workspace
   ```

4. **Register in** `agent/run.py`:
   ```python
   # In setup_thread_manager()
   my_tool = MyNewTool(project_id=project_id)
   thread_manager.register_tool(my_tool, functions=["my_function"])
   ```

5. **Add to System Prompt** if needed in `agent/prompt.py`

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

### Required Variables

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

# Storage
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET_NAME=
S3_ENDPOINT=
S3_REGION=

# Data Providers (Optional)
RAPID_API_KEY=  # For LinkedIn, Twitter, etc.
```

### Configuration Classes

Configuration is managed through `utils/config.py` with validation:
- `LocalConfig`: Development settings
- `ProductionConfig`: Production settings with stricter requirements
- `Config`: Factory that returns appropriate config based on `ENV_MODE`

## Available Tools

### 1. **Computer Use Tool** (`computer_use_tool.py`)
- Low-level automation: mouse, keyboard, screenshots
- Methods: `move_to`, `click`, `typing`, `hotkey`, `get_screenshot_base64`
- Requires automation service at port 8000

### 2. **Browser Tool** (`sb_browser_tool.py`)
- High-level browser automation
- Navigation, element interaction, tab management
- Methods: `browser_navigate_to`, `browser_click_element`, `browser_input_text`
- Returns screenshots with S3 upload

### 3. **Files Tool** (`sb_files_tool.py`)
- File system operations in `/workspace`
- Methods: `create_file`, `str_replace`, `full_file_rewrite`, `delete_file`
- Automatic parent directory creation
- Binary file exclusion patterns

### 4. **Shell Tool** (`sb_shell_tool.py`)
- Command execution with tmux sessions
- Methods: `execute_command`, `check_command_output`, `terminate_command`
- Supports blocking/non-blocking execution
- Named sessions for process management

### 5. **Web Search Tool** (`web_search_tool.py`)
- Tavily API integration for web search
- Firecrawl for content extraction
- Methods: `web_search`, `scrape_webpage`
- Results saved to `/workspace/scrape/`

### 6. **Vision Tool** (`sb_vision_tool.py`)
- Image processing for agent context
- Supports JPG, PNG, GIF, WEBP
- 10MB file size limit
- Converts to base64 for LLM

### 7. **Deploy Tool** (`sb_deploy_tool.py`)
- Deploy to Cloudflare Pages
- Deploys to `{name}.kortix.cloud`
- Uses wrangler CLI

### 8. **Expose Tool** (`sb_expose_tool.py`)
- Expose sandbox ports publicly
- Returns preview URLs
- Port range: 1-65535

### 9. **Data Providers Tool** (`data_providers_tool.py`)
- Third-party API integrations
- Providers: LinkedIn, Yahoo Finance, Amazon, Zillow, Twitter
- Methods: `get_data_provider_endpoints`, `execute_data_provider_call`

### 10. **Message Tool** (`message_tool.py`)
- User interaction and communication
- Methods: `ask`, `web_browser_takeover`, `complete`
- Supports file attachments

## AgentPress Framework

### Architecture Overview

AgentPress is the core framework managing agent execution:

1. **Tool System** (`agentpress/tool.py`)
   - Base `Tool` class with schema registration
   - Decorators: `@openapi_schema`, `@xml_schema`
   - Standardized `ToolResult` responses

2. **Tool Registry** (`agentpress/tool_registry.py`)
   - Centralized tool management
   - Supports OpenAPI and XML formats
   - Dynamic tool discovery

3. **Thread Manager** (`agentpress/thread_manager.py`)
   - Conversation orchestration
   - LLM API integration
   - Auto-continue logic for tool calls
   - Token usage tracking

4. **Response Processor** (`agentpress/response_processor.py`)
   - Parses LLM responses
   - Extracts and executes tool calls
   - Handles streaming and non-streaming
   - XML and native tool format support

5. **Context Manager** (`agentpress/context_manager.py`)
   - Prevents token limit overflow
   - Automatic summarization at 120k tokens
   - Smart message windowing

### Message Flow

1. User message → ThreadManager
2. Context check → Token counting
3. LLM call → With tool schemas
4. Response processing → Tool extraction
5. Tool execution → Sequential/parallel
6. Result storage → Database
7. Auto-continue → If needed
8. Final response → To user

## Database Schema

### Core Tables (AgentPress)

- **projects**: Top-level organization unit
  - Links to accounts, contains sandbox config
  - Can be public or private

- **threads**: Conversation containers
  - Belong to projects or accounts directly
  - Support public sharing

- **messages**: Individual conversation messages
  - Type classification (user/assistant/tool/status)
  - JSONB content for flexibility
  - Metadata storage

- **agent_runs**: Execution session tracking
  - Status: running/completed/failed
  - Timing and error information

### Key Functions

- `get_llm_formatted_messages(thread_id)`: Smart message retrieval with summarization
- `basejump.has_role_on_account()`: Core RLS authorization

### Multi-tenancy (BasejumpJS)

- **accounts**: Personal and team accounts
- **account_user**: User-account relationships
- **invitations**: Team invitation system
- **billing_customers/subscriptions**: Stripe integration

## Real-time Streaming Architecture

### Redis Infrastructure

**Keys:**
- `agent_run:{id}:responses` - Message list (24hr TTL)
- `active_run:{instance}:{id}` - Active run tracking

**Channels:**
- `agent_run:{id}:new_response` - New message notifications
- `agent_run:{id}:control` - Stop/control signals

### SSE Flow

1. Client connects to `/stream` endpoint
2. Initial messages fetched from Redis list
3. Subscribe to pub/sub for new messages
4. Stream updates as they arrive
5. Handle control signals for termination

### Message Types

- `assistant`: AI responses with chunks
- `tool`: Tool execution results
- `status`: Execution status updates
- `cost`: Token usage information

## Testing (Currently Missing)

### Recommended Setup

1. **Install pytest**:
   ```bash
   poetry add --dev pytest pytest-asyncio pytest-cov
   ```

2. **Create test structure**:
   ```
   backend/tests/
   ├── conftest.py
   ├── unit/
   ├── integration/
   └── e2e/
   ```

3. **Run tests**:
   ```bash
   poetry run pytest --cov=. --cov-report=term-missing
   ```

## Debugging Tips

### Common Issues and Solutions

1. **LLM API Issues**:
   - Check `services/llm.py` logs for API failures
   - Verify model name format (e.g., "anthropic/claude-3-7-sonnet-latest")
   - Enable Langfuse for detailed LLM call tracing
   - Check token limits for specific models

2. **Tool Execution Errors**:
   - Check `run_agent_background.py` logs
   - Verify tool registration in `agent/run.py`
   - Check tool schema decorators (@openapi_schema, @xml_schema)
   - Monitor Redis for tool execution messages

3. **Database Issues**:
   - Verify Supabase credentials in `.env`
   - Check RLS policies with `basejump.has_role_on_account()`
   - Ensure migrations are applied: `supabase db push`
   - Test with service role key for debugging

4. **Redis/Streaming Issues**:
   - Verify Redis connection (host: 'redis' for Docker, 'localhost' for local)
   - Check Redis pub/sub channels: `agent_run:{id}:new_response`
   - Monitor Redis lists: `agent_run:{id}:responses`
   - Verify SSE endpoint authentication

5. **Sandbox Issues**:
   - Check Daytona API key and server URL
   - Verify sandbox creation in project record
   - Check `/workspace` path permissions
   - Monitor sandbox resource usage

6. **Tool-Specific Debugging**:
   - **Browser Tool**: Check automation API at port 8000
   - **Shell Tool**: Verify tmux sessions with `tmux ls`
   - **Files Tool**: Check path cleaning and exclusion patterns
   - **Web Search**: Verify Tavily/Firecrawl API keys

## Performance Considerations

1. **Database Optimization**:
   - Use connection pooling for Supabase when possible
   - Leverage indexes on foreign keys and timestamp fields
   - Use `get_llm_formatted_messages()` for efficient message retrieval

2. **Token Management**:
   - Monitor token usage with ContextManager (default: 120k tokens)
   - Automatic summarization at token threshold
   - Summary target size: 10k tokens

3. **Streaming Optimization**:
   - Use Redis pub/sub for real-time message delivery
   - Implement message buffering with Redis lists (24hr TTL)
   - Batch Redis operations with `asyncio.create_task()`

4. **Caching Strategies**:
   - Cache LLM responses when appropriate
   - Use Redis for session state management
   - Implement 15-minute cache for web fetch operations

5. **Resource Management**:
   - Sandbox limits: 2 CPU, 4GB RAM, 5GB disk
   - Implement execution timeouts for tools
   - Use parallel tool execution when possible

## Security Guidelines

### Critical Security Issues to Address

1. **JWT Signature Verification**: Currently disabled in `auth_utils.py` - MUST be enabled
2. **Rate Limiting**: No application-level rate limiting - vulnerable to abuse
3. **Input Validation**: Limited validation on API endpoints
4. **CORS Configuration**: Remove hardcoded IP addresses from allowed origins

### Security Best Practices

1. Always validate and sanitize user inputs using Pydantic models
2. Use proper authentication checks on all endpoints via `Depends(get_current_user_id_from_jwt)`
3. Keep API keys secure and never commit them - use environment variables
4. Sandbox all user-generated code execution through Daytona containers
5. Implement proper error handling without exposing sensitive information
6. Enable comprehensive audit logging for security events
7. Use parameterized queries for any raw SQL operations
8. Implement CSRF protection for state-changing operations