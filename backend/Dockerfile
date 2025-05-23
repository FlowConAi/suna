FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENV_MODE="production" \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x for npx (required for MCP servers)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install uv globally for Python package management (required for MCP servers)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    chmod +x /usr/local/bin/uv /usr/local/bin/uvx

# Create non-root user and set up directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Install Python dependencies
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Switch to non-root user
USER appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Expose the port the app runs on
EXPOSE 8000

# Calculate optimal worker count based on 16 vCPUs
# Using (2*CPU)+1 formula for CPU-bound applications
ENV WORKERS=33
ENV THREADS=2
ENV WORKER_CONNECTIONS=2000

# Gunicorn configuration
CMD ["sh", "-c", "gunicorn api:app \
     --workers $WORKERS \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --timeout 1800 \
     --graceful-timeout 600 \
     --keep-alive 1800 \
     --max-requests 0 \
     --max-requests-jitter 0 \
     --forwarded-allow-ips '*' \
     --worker-connections $WORKER_CONNECTIONS \
     --worker-tmp-dir /dev/shm \
     --preload \
     --log-level info \
     --access-logfile - \
     --error-logfile - \
     --capture-output \
     --enable-stdio-inheritance \
     --threads $THREADS"]
