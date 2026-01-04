# Stage 1: Build stage
FROM python:3.13-alpine AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Prevent uv from copying the project into the venv (keeps it small)
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project --no-dev

# Stage 2: Runtime stage
FROM python:3.13-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
WORKDIR /app

# Copy virtual environment
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy source and static files
COPY --chown=appuser:appgroup ./src ./src
COPY --chown=appuser:appgroup ./static ./static

USER appuser
ENV PATH="/app/.venv/bin:$PATH"

# Use 'python -m' to run fastapi; it's more reliable than the direct bin path
CMD ["python", "-m", "fastapi", "run", "src/main.py", "--port", "8000"]
