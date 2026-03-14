# actBI Monorepo

AI-powered Business Intelligence platform that combines internal business data with external sources.

## Quick Start

```bash
# Install Just (task runner)
brew install just  # macOS
# or: https://github.com/casey/just#installation

# Install dependencies
just setup

# Start development servers
just dev-admin      # Admin dashboard
just dev-xms        # Prompt manager
just dev-pipelines  # Dagster UI
```

## Structure

```
actbi/
├── web/                    # Next.js applications
│   ├── admin/              # Admin dashboard
│   ├── xms/                # Prompt management
│   ├── bi/                 # BI dashboard
│   └── shared/             # Shared TypeScript (hooks, utils)
├── agents/                 # Multi-agent AI system
├── evals/                  # Agent evaluation framework
├── pipelines/              # Dagster pipelines (~90 assets)
├── xlake/                  # Semantic data layer (Python SDK)
├── notebooks/              # Jupyter exploration environment
├── lib/                    # Shared Python packages
│   ├── io/                 # File I/O utilities
│   ├── data/               # Asset loading
│   └── prompts/            # Prompt templates
├── service/                # FastAPI HTTP API
├── knowledge/              # RAG knowledge bases
├── third_party/            # Vendored dependencies
└── docs/                   # Documentation
```

## Commands

Run `just --list` for all available commands.

### Development
- `just dev-admin` - Start admin dashboard
- `just dev-xms` - Start XMS
- `just dev-pipelines` - Start Dagster UI

### Testing
- `just test` - Run all tests
- `just test-python` - Python tests only
- `just test-js` - JavaScript tests only

### Linting
- `just lint` - Lint all code
- `just format` - Format all code

## Documentation

- [AI Instructions](AI_INSTRUCTIONS.md) - For Claude Code/Cursor
- [Pipelines](pipelines/README.md) - Dagster data ingestion
- [Agents](agents/README.md) - Multi-agent AI system
- [Admin App](web/admin/README.md) - Admin dashboard
- [XMS App](web/xms/README.md) - Prompt manager
- **[Local Supabase setup (new developers)](docs/SUPABASE-LOCAL-SETUP-FOR-NEW-DEVELOPERS.md)** — Install Docker + Supabase CLI and run local DB with seed (step-by-step)

## Requirements

- Node.js 20+
- Python 3.12+
- pnpm 9+
- uv (Python package manager)
- Just (task runner)
- **Local Supabase:** Docker Desktop + Supabase CLI (see [Supabase setup guide](docs/SUPABASE-LOCAL-SETUP-FOR-NEW-DEVELOPERS.md))
