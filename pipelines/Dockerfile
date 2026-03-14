# D1-01: Multi-stage Dagster image (webserver + daemon, no dbt).
# Build from repo root: docker build -f pipelines/Dockerfile -t pipelines:latest .
# Base: python:3.12-slim

# -----------------------------------------------------------------------------
# Builder: install deps and workspace packages
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv and system deps for building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Copy workspace root and workspace members needed by pipelines
COPY pyproject.toml uv.lock ./
COPY lib/io lib/io
COPY lib/data lib/data
COPY pipelines pipelines

# Install pipelines and its dependencies (shared-io, shared-data via workspace)
RUN uv sync --frozen --package pipelines --no-dev

# -----------------------------------------------------------------------------
# Runtime: copy venv and code; same paths so editable installs work
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy venv and workspace source (editable installs point to /app/lib, /app/pipelines)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/lib /app/lib
COPY --from=builder /app/pipelines /app/pipelines
COPY --from=builder /app/pyproject.toml /app/uv.lock ./

ENV PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv" \
    DAGSTER_HOME=/opt/dagster_home

RUN mkdir -p ${DAGSTER_HOME}

EXPOSE 3000

# Default: run webserver; override with "dagster-daemon run" for daemon
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
