# TCMB MCP - Multi-stage Dockerfile

# Stage 1: Builder
FROM python:3.10-slim AS builder

WORKDIR /app

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install .

# Stage 2: Runtime
FROM python:3.10-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code
COPY src ./src

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV TCMB_CACHE_DB_PATH=/app/data/tcmb_cache.db
ENV TCMB_DEBUG=false
ENV TCMB_LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import tcmb_mcp; print('OK')" || exit 1

# Run the MCP server
CMD ["python", "-m", "tcmb_mcp"]
