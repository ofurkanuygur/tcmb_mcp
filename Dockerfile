# TCMB MCP - Smithery Deployment Dockerfile
# Using official uv image for efficient Python dependency management

FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

# Enable bytecode compilation and copy mode
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first (better caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy application code
COPY . /app

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Environment variables for Smithery
ENV MCP_TRANSPORT=http
ENV PORT=8080

# Clear entrypoint from base image
ENTRYPOINT []

# Run the MCP server
CMD ["python", "-m", "tcmb_mcp"]
