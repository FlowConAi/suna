# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Suna is an open-source generalist AI agent that helps users accomplish real-world tasks through natural conversation. The system integrates browser automation, file management, web search, command-line execution, and various APIs to solve complex problems. Detailed documentation is available in the `backend/CLAUDE.md` and `frontend/CLAUDE.md` files.

## Architecture

Suna consists of four main components:

1. **Backend API** (Python/FastAPI): Handles REST endpoints, thread management, LLM integration via LiteLLM, and orchestrates a robust tool system with various capabilities
2. **Frontend** (Next.js/React): Provides the responsive user interface with real-time chat, tool result visualization, and project management dashboard
3. **Agent Docker**: Isolated execution environments (Daytona sandboxes) with browser automation, file system access, and secure tool execution
4. **Infrastructure Services**: Redis for state management and message streaming, RabbitMQ for task queuing, and Supabase for authentication and data persistence

## Development Commands

### Backend

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

### Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint

# Format code
npm run format
```

### Project Management

```bash
# Start or stop all containers
python start.py

# Setup project with wizard
python setup.py
```

## Repository Structure

The codebase is organized into two main directories with component-specific CLAUDE.md files for detailed guidance:

- **backend/**: Python-based FastAPI application with agent execution logic, tool implementation, and service integrations
- **frontend/**: Next.js application with React components for the user interface

See `backend/CLAUDE.md` and `frontend/CLAUDE.md` for detailed documentation on each component.

## LLM Integration

The LLM service (`backend/services/llm.py`) provides a unified interface for making API calls to various language models using LiteLLM. The Langfuse integration (`backend/services/langfuse_integration.py`) provides observability for LLM API calls, tracking usage, costs, and performance metrics.

### Supported Models

- **Anthropic**: Claude 3.7 Sonnet, Claude 3.5 Haiku, etc.
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Google**: Gemini models via Vertex AI
- **AWS Bedrock**: Various models
- **OpenRouter**: Access to multiple providers

### Model Configuration

Set default model in `.env`:
```
MODEL_TO_USE=anthropic/claude-3-7-sonnet-latest
```

Models can be changed per request through the API.

### Langfuse Configuration

To enable Langfuse observability, add the following to the `.env` file:

```
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to cloud.langfuse.com
```

### AgentPress Framework

Suna uses the custom AgentPress framework for agent orchestration:

- **Tool Management**: Dynamic tool registration with multiple schema formats
- **Context Management**: Automatic summarization at token limits
- **Response Processing**: Streaming and non-streaming with tool execution
- **Multi-format Support**: OpenAPI and XML tool calling formats

See `backend/CLAUDE.md` for detailed AgentPress documentation.

### MCP (Model Context Protocol) Integration

Suna supports integration with MCP servers, enabling connections to external tools and services:

- **Built-in MCP Servers**:
  - **context7**: Real-time documentation lookup for libraries and frameworks
  - **basic-memory**: Persistent memory storage across agent sessions
  - **atlassian**: Jira and Confluence integration for project management

- **Key Features**:
  - Dynamic tool discovery and registration
  - Support for multiple concurrent MCP servers
  - Security through tool whitelisting/blacklisting
  - Automatic error handling and graceful degradation

See `backend/agentpress/mcp/CLAUDE.md` for MCP architecture details and `backend/docs/MCP_ATLASSIAN_SETUP.md` for Atlassian setup instructions.

## Environment Configuration

The project uses environment variables for configuration, with separate `.env` files for backend and frontend.

Important environment variables:
- `REDIS_HOST`: Redis server hostname (use 'redis' for Docker-to-Docker, 'localhost' for local-to-Docker)
- `RABBITMQ_HOST`: RabbitMQ hostname (same principle as Redis)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`: Supabase connection details
- `MODEL_TO_USE`: Default LLM model to use (e.g., "anthropic/claude-3-7-sonnet-latest")
- Various API keys for LLM providers, search services, and other integrations
- **Atlassian MCP Integration** (optional):
  - `CONFLUENCE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN`: Confluence access
  - `JIRA_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`: Jira access

## Database Migrations

Supabase migrations are stored in `backend/supabase/migrations/`. To apply migrations:

```bash
cd backend
supabase db push
```

## Quick Start Guide

1. Clone the repository and navigate to the root directory
2. Run `python setup.py` to configure environment files and dependencies
3. Start the backend services with `docker compose up redis rabbitmq -d`
4. In separate terminals, run:
   - Backend API: `cd backend && poetry run python3.11 api.py`
   - Background worker: `cd backend && poetry run python3.11 -m dramatiq run_agent_background`
   - Frontend: `cd frontend && npm run dev`
5. Access the application at http://localhost:3000

## Security Warnings

⚠️ **Critical Security Issues to Address**:

1. **JWT Signature Verification Disabled**: The backend currently has JWT signature verification disabled in `backend/utils/auth_utils.py`. This MUST be enabled in production.
2. **No Rate Limiting**: The application lacks rate limiting, making it vulnerable to abuse.
3. **Hardcoded Values**: Several sensitive values are hardcoded and should be moved to environment variables.

See `backend/CLAUDE.md` for detailed security guidelines.

## Troubleshooting Common Issues

1. **API Health Check Issues**: If you see maintenance pages, check API connectivity with `curl http://localhost:8000/api/health`
2. **Environment Configuration**: Verify `.env` files exist in both frontend and backend directories
3. **Database Connection**: Ensure Supabase credentials are correct in backend/.env
4. **Browser-side blocking**: If browser shows "ERR_BLOCKED_BY_CLIENT", check browser extensions/settings
5. **Redis Connection Issues**: 
   - Use 'localhost' when running API locally and Redis in Docker
   - Use 'redis' when both are in Docker
   - Check with `redis-cli ping`
6. **Streaming Not Working**:
   - Verify authentication token is passed correctly
   - Check browser console for EventSource errors
   - Ensure CORS is configured properly
7. **Tool Execution Failures**:
   - Check sandbox is running: look for Daytona status
   - Verify tool registration in `agent/run.py`
   - Check tool-specific API keys in `.env`

For component-specific guidance, refer to `backend/CLAUDE.md` and `frontend/CLAUDE.md`.

## Testing Strategy

### Current State
The project currently lacks comprehensive testing. Both backend and frontend have testing frameworks in dependencies but no actual tests.

### Recommended Implementation

1. **Backend Testing** (pytest):
   ```bash
   cd backend
   poetry add --dev pytest pytest-asyncio pytest-cov
   poetry run pytest --cov=. --cov-report=term-missing
   ```

2. **Frontend Testing** (Jest + React Testing Library):
   ```bash
   cd frontend
   npm install --save-dev jest @testing-library/react
   npm run test
   ```

3. **E2E Testing** (Playwright):
   ```bash
   npm install --save-dev @playwright/test
   npx playwright test
   ```

See individual CLAUDE.md files for detailed testing setup instructions.

## Deployment Guide

### Production Deployment

1. **Backend Deployment** (Fly.io):
   ```bash
   cd backend
   fly deploy --config fly.production.toml
   ```

2. **Frontend Deployment** (Vercel/Netlify):
   ```bash
   cd frontend
   npm run build
   # Deploy dist/ folder
   ```

3. **Database Setup**:
   - Run migrations: `supabase db push`
   - Configure RLS policies
   - Set up billing integration

4. **Required Services**:
   - Redis (with persistence enabled)
   - RabbitMQ (for background tasks)
   - S3-compatible storage (for file uploads)
   - Daytona (for sandboxes)

### Environment-Specific Configuration

- **Production**: Strict CORS, enabled auth, production API keys
- **Staging**: Relaxed CORS, test API keys, debug logging
- **Development**: Local services, mock integrations available

## Architecture Diagrams

Detailed architecture diagrams are available in:
- `docs/images/architecture_diagram.svg` - System overview
- `docs/analysis/` - Detailed component analysis

## Contributing Guidelines

See `CONTRIBUTING.md` for:
- Code style guidelines
- PR process
- Development setup
- Testing requirements