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

### Langfuse Configuration

To enable Langfuse observability, add the following to the `.env` file:

```
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to cloud.langfuse.com
```

## Environment Configuration

The project uses environment variables for configuration, with separate `.env` files for backend and frontend.

Important environment variables:
- `REDIS_HOST`: Redis server hostname (use 'redis' for Docker-to-Docker, 'localhost' for local-to-Docker)
- `RABBITMQ_HOST`: RabbitMQ hostname (same principle as Redis)
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`: Supabase connection details
- `MODEL_TO_USE`: Default LLM model to use (e.g., "anthropic/claude-3-7-sonnet-latest")
- Various API keys for LLM providers, search services, and other integrations

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

## Troubleshooting Common Issues

1. **API Health Check Issues**: If you see maintenance pages, check API connectivity with `curl http://localhost:8000/api/health`
2. **Environment Configuration**: Verify `.env` files exist in both frontend and backend directories
3. **Database Connection**: Ensure Supabase credentials are correct in backend/.env
4. **Browser-side blocking**: If browser shows "ERR_BLOCKED_BY_CLIENT", check browser extensions/settings

For component-specific guidance, refer to `backend/CLAUDE.md` and `frontend/CLAUDE.md`.