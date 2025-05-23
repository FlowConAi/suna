# Suna Backend

## Running the backend

Within the backend directory, run the following command to stop and start the backend:

```bash
docker compose down && docker compose up --build
```

## Running Individual Services

You can run individual services from the docker-compose file. This is particularly useful during development:

### Running only Redis and RabbitMQ

```bash
docker compose up redis rabbitmq
```

### Running only the API and Worker

```bash
docker compose up api worker
```

## Development Setup

For local development, you might only need to run Redis and RabbitMQ, while working on the API locally. This is useful when:

- You're making changes to the API code and want to test them directly
- You want to avoid rebuilding the API container on every change
- You're running the API service directly on your machine

To run just Redis and RabbitMQ for development:

```bash
docker compose up redis rabbitmq
```

Then you can run your API service locally with the following commands

```sh
# On one terminal
cd backend
poetry run python3.11 api.py

# On another terminal
cd frontend
poetry run python3.11 -m dramatiq run_agent_background
```

## LLM Service and Langfuse Integration

The LLM service (`services/llm.py`) provides a unified interface for making API calls to various language models (OpenAI, Anthropic, OpenRouter, AWS Bedrock, etc.) using LiteLLM.

### Features

- Unified API for multiple LLM providers
- Streaming support
- Tool/function calling
- Retry logic with exponential backoff
- Comprehensive error handling
- Optional Langfuse observability integration

### Langfuse Observability Integration

The Langfuse integration (`services/langfuse_integration.py`) provides observability for LLM API calls. This is an optional feature that allows you to track usage, costs, and performance metrics for your LLM API calls.

#### Configuration

To enable Langfuse observability, add the following to your `.env` file:

```
# Langfuse Configuration
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional, defaults to cloud.langfuse.com
```

You can get your Langfuse API keys by signing up at [Langfuse](https://langfuse.com/).


#### Fallback Behavior

The Langfuse integration is designed to be completely optional and non-blocking:

- If Langfuse is not configured, the application will continue to function normally without observability
- If there are errors during Langfuse integration, they will be logged as warnings and the application will continue
- The core LLM functionality will always work, even if Langfuse integration fails

## Environment Configuration

When running services individually, make sure to:

1. Check your `.env` file and adjust any necessary environment variables
2. Ensure Redis connection settings match your local setup (default: `localhost:6379`)
3. Ensure RabbitMQ connection settings match your local setup (default: `localhost:5672`)
4. Update any service-specific environment variables if needed

### Important: Redis Host Configuration

When running the API locally with Redis in Docker, you need to set the correct Redis host in your `.env` file:

- For Docker-to-Docker communication (when running both services in Docker): use `REDIS_HOST=redis`
- For local-to-Docker communication (when running API locally): use `REDIS_HOST=localhost`

### Important: RabbitMQ Host Configuration

When running the API locally with Redis in Docker, you need to set the correct RabbitMQ host in your `.env` file:

- For Docker-to-Docker communication (when running both services in Docker): use `RABBITMQ_HOST=rabbitmq`
- For local-to-Docker communication (when running API locally): use `RABBITMQ_HOST=localhost`

Example `.env` configuration for local development:

```sh
REDIS_HOST=localhost (instead of 'redis')
REDIS_PORT=6379
REDIS_PASSWORD=

RABBITMQ_HOST=localhost (instead of 'rabbitmq')
RABBITMQ_PORT=5672
```
