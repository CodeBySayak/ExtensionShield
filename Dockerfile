# ExtensionShield Dockerfile
# Multi-stage build: Node.js for frontend, Python for backend

# =============================================================================
# Stage 1: Build React Frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install build dependencies for node-gyp and native modules
RUN apk add --no-cache python3 make g++

# Copy package files first for better layer caching
COPY frontend/package*.json ./

# Install dependencies with increased memory for production builds
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build production bundle
RUN npm run build

# =============================================================================
# Stage 2: Python Backend with Frontend Static Files
# =============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install system dependencies
# - git: required by some Python packages and semgrep
# - curl: for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files and README (required by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

# Copy application source code (needed for package build)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docs/supabase_migrations/ ./docs/supabase_migrations/

# Install Python dependencies and build the project
RUN uv sync --frozen --no-dev

# Prefer running the installed venv entrypoints directly (faster startup than `uv run`)
ENV PATH="/app/.venv/bin:$PATH"

# Copy frontend build from stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Create necessary directories
RUN mkdir -p extensions_storage data

# Set default environment variables
ENV EXTENSION_STORAGE_PATH=/app/extensions_storage \
    DATABASE_PATH=/app/data/extension-shield.db \
    LLM_PROVIDER=openai

# Default port (Railway will override with PORT env var)
ENV PORT=8007

# Expose the API port
EXPOSE 8007

# Health check - uses PORT env var that Railway injects
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:${PORT:-8007}/health || exit 1

# Run the application with migrations (Supabase only)
CMD ["sh", "/app/scripts/start_api.sh"]
