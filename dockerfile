FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:0.5.13-python3.12-alpine AS base

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./
COPY mysql-mcp/pyproject.toml mysql-mcp/uv.lock mysql-mcp/README.md mysql-mcp/.python-version ./mysql-mcp/
COPY mysql-mcp/src ./mysql-mcp/src

# Use the exact Python interpreter path
ENV PYTHONPATH=/usr/local/bin/python3.12
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_VIRTUALENV=$VIRTUAL_ENV

# Create venv with explicit Python path
RUN uv venv --python=$PYTHONPATH $VIRTUAL_ENV && \
    uv sync && \
    cd mysql-mcp && \
    uv venv --python=$PYTHONPATH .venv && \
    uv sync

# Development stage
FROM base AS development

# Copy source code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/usr/local/bin/python3.12
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_VIRTUALENV=$VIRTUAL_ENV

# Production stage for API service
FROM ghcr.io/astral-sh/uv:0.5.13-python3.12-alpine AS api

WORKDIR /app

# Copy virtual environment and application files
COPY --from=base /app/.venv /app/.venv
COPY --from=base /app/mysql-mcp/.venv /app/mysql-mcp/.venv
COPY ./app ./app
COPY ./mysql-mcp ./mysql-mcp
COPY mcp_config.json .
COPY main.py .
COPY uv.lock .

# Create non-root user
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/usr/local/bin/python3.12
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_VIRTUALENV=$VIRTUAL_ENV

# Command to run the API service
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]