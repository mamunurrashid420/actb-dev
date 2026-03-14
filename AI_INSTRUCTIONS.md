# AI Instructions - actBI Monorepo

This file provides context for AI assistants (Claude Code, Cursor) working on the actBI monorepo.

## Project Overview

actBI is an AI-powered Business Intelligence platform that combines companies' internal data with external sources to enable data-driven decision making.

### Architecture

```
actbi/
├── web/                    # User-facing web applications
│   ├── admin/              # Admin dashboard (tenant/user management)
│   ├── xms/                # Prompt management system
│   ├── bi/                 # BI dashboard with chat and visualizations
│   └── shared/             # Shared TypeScript: hooks, utils, components
│
├── agents/                 # AI intelligence layer (multi-agent system)
│
├── evals/                  # Evaluation framework for agents
│   ├── src/evals/          # Framework code
│   └── notebooks/          # Eval notebooks
│
├── pipelines/              # Data ingestion (Dagster, ~90 assets)
│
├── xlake/                  # Semantic data layer (Python SDK)
│
├── service/                # HTTP API (FastAPI)
│
├── knowledge/              # RAG knowledge bases
│   └── data-viz-bible/     # Visualization guidance
│
├── lib/                    # Core shared libraries
│   ├── io/                 # shared.io - File I/O, asset storage
│   ├── data/               # shared.data - Asset loading, SEC utilities
│   └── prompts/            # shared.prompts - Versioned prompt storage
│
├── notebooks/              # Jupyter exploration environment
│
├── docs/                   # Documentation
│   └── architecture/       # Architecture docs and ADRs
│
└── third_party/            # Vendored external code
    └── react-graph-gallery/  # D3.js chart library
```

**Shared Code Organization:**
- `web/shared/` - TypeScript/React: hooks, utilities (@actbi/shared)
- `lib/` - Python: namespace packages (`from shared.io import ...`, `from shared.data import ...`)

## Technology Stack

### Web Applications (web/)
- **Framework**: Next.js 15.5.x with App Router
- **React**: 19.x
- **Styling**: Tailwind CSS 4.x
- **UI Components**: shadcn/ui + Radix UI
- **State**: Zustand, TanStack Query
- **Forms**: React Hook Form + Zod
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth with RBAC

### Python Platform
- **Python**: 3.12+
- **Package Manager**: UV with workspaces
- **Orchestration**: Dagster
- **Data Processing**: Pandas, Polars, DuckDB
- **Storage**: Parquet files (local/S3)
- **Vector Search**: Qdrant
- **Serialization**: Protocol Buffers

## Hierarchical Documentation

Each area has its own `AI_INSTRUCTIONS.md` with specific context:

```
AI_INSTRUCTIONS.md                    # This file (root)
├── @agents/AI_INSTRUCTIONS.md        # Agent patterns
├── @evals/AI_INSTRUCTIONS.md         # Evaluation framework
├── @pipelines/AI_INSTRUCTIONS.md     # Pipeline patterns
├── @xlake/AI_INSTRUCTIONS.md         # Semantic layer
├── @notebooks/AI_INSTRUCTIONS.md     # Jupyter environment
├── @lib/AI_INSTRUCTIONS.md           # Shared Python packages
└── @web/AI_INSTRUCTIONS.md           # Web app patterns
    ├── @admin/AI_INSTRUCTIONS.md
    ├── @xms/AI_INSTRUCTIONS.md
    └── @bi/AI_INSTRUCTIONS.md
```

## Key Commands

All commands are available via `just`:

```bash
# Setup
just setup              # Install all dependencies

# Development
just dev-admin          # Admin dashboard (port 3000)
just dev-xms            # XMS (port 3001)
just dev-bi             # BI dashboard (port 3002)
just dev-pipelines      # Dagster UI (port 3000)

# Testing
just test               # All tests
just test-python        # Python tests
just test-js            # JavaScript tests
just test-agents        # Agent tests
just test-evals-integration  # Eval integration tests

# Linting
just lint               # Lint all
just format             # Format all

# Dagster
just dagster-check      # Validate definitions
just dagster-schedules  # List schedules
```

## Coding Standards

### Python
- Direct imports: `from dagster import asset`, `from pathlib import Path`
- Standard aliases only: `import pandas as pd`, `import numpy as np`
- Type hints on all functions
- Single-line docstrings preferred
- Method chaining for pandas/polars operations
- Double quotes for strings
- See `docs/CODING_STANDARDS.md` for full guide

### TypeScript (web/)
- Functional components with hooks
- Use `@/*` path aliases
- Zod for validation
- Server Components by default
- See each app's README for specific patterns

## Database

Single Supabase project shared across all web apps:

| App | Tables Used |
|-----|-------------|
| admin/bi | tenants, users, roles, permissions, conversations, messages |
| xms | prompts, snippets, variables |

Each web app manages its own Supabase migrations in `web/{app}/supabase/migrations/`.

## External Data Sources

The data platform integrates with 11+ sources:
- **Economic**: FRED, BLS, BEA, World Bank, ECB
- **Corporate**: SEC EDGAR (10-K, 10-Q, Form 4, 13-F, FSDS)
- **Agriculture**: USDA, NASA POWER
- **Other**: PatentsView, NOAA

See `pipelines/AI_INSTRUCTIONS.md` for asset details.

## Working with This Codebase

### Before Implementation
1. **Read relevant files**: Understand existing code before modifying
2. **Check for existing solutions**: Search the codebase for similar implementations
3. **Research libraries and best practices**: Before writing custom code, search for well-maintained third-party packages and established patterns. Prefer proven libraries over custom implementations.

### During Implementation
4. **Follow existing patterns**: Match the style and approach of surrounding code
5. **Run tests**: `just test` after changes
6. **Validate Dagster**: `just dagster-check` after pipeline changes

### Before Committing
7. **Lint and format**: Run `just lint` and `just format`
8. **No AI Co-Author tags**: Do not include "Co-Authored-By" lines attributing AI agents (e.g., Claude, Copilot) in commit messages
