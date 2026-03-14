# actBI Monorepo - Unified Task Runner
# Usage: just <recipe>

# Default recipe - show available commands
default:
    @just --list

# =============================================================================
# Setup
# =============================================================================

# Install all dependencies (Python + JavaScript) and git hooks
setup: setup-python setup-js setup-hooks setup-kernel

# Install only Python dependencies
setup-python:
    uv sync --all-packages

# Install only JavaScript dependencies
setup-js:
    pnpm install

# Install git hooks (pre-commit + post-merge for proto generation)
setup-hooks:
    #!/usr/bin/env bash
    set -e
    # Determine hooks directory (handle worktrees)
    if [ -f .git ]; then
        hooks_dir=$(cat .git | sed 's/gitdir: //')/hooks
    else
        hooks_dir=.git/hooks
    fi
    mkdir -p "$hooks_dir"

    # Clean up hooks we manage (add obsolete hooks here when removing them)
    rm -f "$hooks_dir/post-merge"

    # Install pre-commit hooks
    uv run pre-commit install

    # Install post-merge hook for proto generation
    cp scripts/post-merge "$hooks_dir/post-merge"
    chmod +x "$hooks_dir/post-merge"

    echo "Git hooks installed"

# Install Jupyter kernel for notebooks
setup-kernel:
    cd notebooks && uv run python scripts/install_kernel.py

# =============================================================================
# Development Servers
# =============================================================================

# Start admin dashboard dev server
dev-admin:
    pnpm --filter '@actbi/admin' dev

# Start xms dev server
dev-xms:
    pnpm --filter '@actbi/xms' dev
# Start bi dashboard dev server
dev-bi:
    pnpm --filter '@actbi/bi' dev


# Start Python API dev server
dev-api:
    cd service && PYTHONPATH=src uv run uvicorn app.main:app --reload --port 8000

# Start Dagster pipeline UI
dev-pipelines:
    cd pipelines && DAGSTER_HOME=.dagster uv run dg dev

# =============================================================================
# Testing
# =============================================================================

# Run all tests
test: test-python test-js

# Run all Python tests (auto-discovers workspace members with tests/)
test-python:
    #!/usr/bin/env bash
    set -e
    members=$(python3 -c "import tomllib; f = open('pyproject.toml', 'rb'); d = tomllib.load(f); print(' '.join(d['tool']['uv']['workspace']['members']))")
    for member in $members; do
        # Check if tests/ exists and has actual test files (test_*.py or *_test.py)
        if [ -d "$member/tests" ] && find "$member/tests" -name "test_*.py" -o -name "*_test.py" 2>/dev/null | grep -q .; then
            echo "=== Testing $member ==="
            (cd "$member" && uv run pytest) || exit 1
        fi
    done

# Run API tests
test-api:
    cd service && PYTHONPATH=src uv run pytest

# Run JavaScript tests
test-js:
    pnpm --filter './web/*' test

# Run admin tests
test-admin:
    pnpm --filter '@actbi/admin' test

# Run xms tests
test-xms:
    pnpm --filter '@actbi/xms' test
# Run bi tests
test-bi:
    pnpm --filter '@actbi/bi' test


# Run pipeline tests
test-pipelines:
    cd pipelines && uv run pytest

# Run xlake tests (generates protos first)
test-xlake: generate-protos
    cd xlake && uv run pytest

# Run shared package tests (io + data)
test-shared:
    cd lib/io && uv run pytest
    cd lib/data && uv run pytest

# Run notebooks tests
test-notebooks:
    cd notebooks && uv run pytest

# Run agent unit tests (fast, no LLM calls)
test-agents:
    cd agents && uv run pytest tests/ -v

# Run eval integration tests (slow, requires LLM API key)
test-evals-integration:
    cd evals && uv run pytest src/evals/ -v -m integration

# Run all agent and eval tests
test-agents-all:
    cd agents && uv run pytest tests/ -v
    cd evals && uv run pytest -v

# =============================================================================
# Agent Evaluations
# =============================================================================

# Run an agent evaluation (usage: just eval <config_name>)
eval config *args:
    cd evals && uv run eval run {{config}} {{args}}

# List stored experiments
eval-list *args:
    cd evals && uv run eval list {{args}}

# Compare two experiment runs
eval-compare id1 id2 *args:
    cd evals && uv run eval compare {{id1}} {{id2}} {{args}}

# Show available eval configs
eval-configs:
    cd evals && uv run eval configs

# =============================================================================
# Linting & Formatting
# =============================================================================

# Lint all code
lint: lint-python lint-js

# Lint Python code
lint-python:
    #!/usr/bin/env bash
    files=$(uv run ruff check . --show-files 2>/dev/null)
    file_count=$(echo "$files" | wc -l)
    dirs=$(echo "$files" | python3 scripts/list-python-dirs.py)
    echo "Linting $file_count files in $dirs"
    uv run ruff check .

# Lint JavaScript code
lint-js:
    pnpm --filter './web/*' lint

# Format all code
format: format-python format-js

# Format Python code
format-python:
    #!/usr/bin/env bash
    files=$(uv run ruff check . --show-files 2>/dev/null)
    file_count=$(echo "$files" | wc -l)
    dirs=$(echo "$files" | python3 scripts/list-python-dirs.py)
    echo "Formatting $file_count files in $dirs"
    uv run ruff check --fix .
    uv run ruff format .

# Format JavaScript code
format-js:
    pnpm --filter './web/*' format

# =============================================================================
# Build
# =============================================================================

# Build all web apps
build-web:
    NODE_OPTIONS="--max-old-space-size=8192" pnpm --filter './web/*' build

# Build admin
build-admin:
    NODE_OPTIONS="--max-old-space-size=8192" pnpm --filter '@actbi/admin' build

# Build xms
build-xms:
    NODE_OPTIONS="--max-old-space-size=8192" pnpm --filter '@actbi/xms' build

# Build bi
build-bi:
    NODE_OPTIONS="--max-old-space-size=8192" pnpm --filter '@actbi/bi' build


# =============================================================================
# Dagster Pipeline Commands
# =============================================================================

# Validate Dagster definitions
dagster-check:
    cd pipelines && uv run dg check defs

# List all Dagster schedules
dagster-schedules:
    cd pipelines && uv run dg schedule list

# =============================================================================
# Database (Supabase) - Single Source of Truth
# =============================================================================

# Start local Supabase (unified database)
db-start:
    cd service/supabase && supabase start

# Stop local Supabase
db-stop:
    cd service/supabase && supabase stop

# Reset database (apply all migrations)
db-reset:
    cd service/supabase && supabase db reset

# Generate TypeScript types for frontends
db-types-ts:
    cd service/supabase && supabase gen types typescript --local > ../../web/bi/src/types/supabase.ts
    cp web/bi/src/types/supabase.ts web/xms/src/types/supabase.ts

# =============================================================================
# Database (Legacy - will be removed after migration)
# =============================================================================

# Start local Supabase for admin
supabase-start-admin:
    cd web/admin && supabase start

# Stop admin Supabase
supabase-stop-admin:
    cd web/admin && supabase stop

# Generate TypeScript types for admin
supabase-types-admin:
    cd web/admin && supabase gen types typescript --local > src/types/supabase.ts

# Start local Supabase for bi
supabase-start-bi:
    cd web/bi && supabase start

# Stop bi Supabase
supabase-stop-bi:
    cd web/bi && supabase stop

# Generate TypeScript types for bi
supabase-types-bi:
    cd web/bi && supabase gen types typescript --local > src/types/supabase.ts

# Start local Supabase for xms (separate project)
supabase-start-xms:
    cd web/xms && supabase start

# Stop xms Supabase
supabase-stop-xms:
    cd web/xms && supabase stop

# =============================================================================
# Security Auditing
# =============================================================================

# Audit all dependencies for vulnerabilities
audit: audit-python audit-js

# Audit Python dependencies (uses pip-audit)
audit-python:
    uvx pip-audit

# Audit JavaScript dependencies
audit-js:
    pnpm audit

# =============================================================================
# Code Generation
# =============================================================================

# Generate protobuf Python files for xlake
generate-protos:
    cd xlake && uv run python scripts/compile_protos.py

# =============================================================================
# Utilities
# =============================================================================

# Clean build artifacts
clean:
    rm -rf web/*/.next
    rm -rf web/*/node_modules/.cache
    find agents pipelines xlake evals lib notebooks -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find agents pipelines xlake evals lib notebooks -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    find service -name "__pycache__" -type d -exec rm -rf {} +
    find service -name ".pytest_cache" -type d -exec rm -rf {} +

# Update react-graph-gallery from upstream
update-graph-gallery:
    git subtree pull --prefix=third_party/react-graph-gallery \
      https://github.com/holtzy/react-graph-gallery.git main --squash
