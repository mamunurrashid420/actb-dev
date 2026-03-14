# Claude Code - actBI Monorepo

@AI_INSTRUCTIONS.md

## Quick Start

```bash
just setup      # Install all dependencies
just dev-admin  # Start admin dashboard
just dev-xms    # Start XMS prompt manager
just dev-pipelines  # Start Dagster UI
```

## Navigation

### Using @ References
- **AI_INSTRUCTIONS.md** - Root AI documentation
- **agents/AI_INSTRUCTIONS.md** - Multi-agent AI system
- **pipelines/AI_INSTRUCTIONS.md** - Dagster data pipelines
- **xlake/AI_INSTRUCTIONS.md** - Semantic data layer
- **lib/AI_INSTRUCTIONS.md** - Shared Python packages
- **web/AI_INSTRUCTIONS.md** - Web applications (admin, xms, bi)

### Project Areas
| Area | Path | Purpose |
|------|------|---------|
| Web Apps | `web/` | Next.js dashboards (admin, xms, bi) |
| Web Shared | `web/shared/` | Shared TypeScript (hooks, utils) |
| Agents | `agents/` | Multi-agent AI system |
| Evals | `evals/` | Agent evaluation framework |
| Pipelines | `pipelines/` | Dagster data ingestion (~90 assets) |
| Xlake | `xlake/` | Semantic data layer (Python SDK) |
| Notebooks | `notebooks/` | Jupyter exploration environment |
| Lib | `lib/` | Shared Python (io, data, prompts) |
| Knowledge | `knowledge/` | RAG knowledge bases |
| Visualizations | `third_party/react-graph-gallery/` | D3.js chart library |

### Working with the Codebase
- **Exploring**: Use Task tool with `subagent_type='Explore'`
- **Searching**: Use Grep for code content, Glob for file patterns
- **Reading**: Use Read tool for viewing files

## Key Commands

```bash
# Development
just dev-admin        # Admin dashboard (Next.js)
just dev-xms          # XMS prompt manager (Next.js)
just dev-pipelines    # Dagster pipeline UI

# Testing
just test             # All tests
just test-python      # Python tests only
just test-js          # JavaScript tests only

# Linting
just lint             # Lint all code
just format           # Format all code

# Dagster
just dagster-check    # Validate pipeline definitions
```
