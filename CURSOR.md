# Cursor - actBI Monorepo

@AI_INSTRUCTIONS.md

## Quick Start

```bash
just setup      # Install all dependencies
just dev-admin  # Start admin dashboard
just dev-xms    # Start XMS prompt manager
```

## Workspace Structure

```
actbi/
├── web/           # Next.js applications
│   ├── admin/     # Admin dashboard
│   ├── xms/       # Prompt management
│   └── bi/        # BI dashboard (pending)
├── data/          # Python data platform
│   ├── pipelines/ # Dagster pipelines
│   ├── xlake/     # Semantic layer
│   └── agents/    # AI agents
├── packages/      # Shared packages
└── third_party/   # Vendored dependencies
```

## Key Files

- `justfile` - All available commands (`just --list`)
- `pnpm-workspace.yaml` - JavaScript workspace
- `pyproject.toml` - Python workspace (UV)
