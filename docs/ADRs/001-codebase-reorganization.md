# ADR-001: Codebase Reorganization

**Status:** Accepted
**Date:** 2026-01-22

## Context

The actBI monorepo has grown organically and now contains multiple projects that aren't logically grouped. The current structure creates confusion:

### Problems with Current Structure

1. **Language-based grouping instead of semantic grouping**
   - The `data/` directory groups "Python stuff" together regardless of purpose
   - `data/agents/`, `data/pipelines/`, `data/xlake/` have different purposes but are siblings because they're Python

2. **Confusing naming**
   - `data/shared/` vs `web/shared/` - same name, different languages
   - `data/analysis/` is actually Jupyter notebooks, not "analysis"
   - `xlake/api/` is an SDK surface, not HTTP endpoints (confusing given `service/` IS HTTP)

3. **Misplaced code**
   - `packages/viz/` is orphaned (not in any workspace)
   - `data/docs/` duplicates `docs/` for architecture documentation
   - Eval framework is nested inside agents but could test multiple systems

4. **Unclear boundaries**
   - What's the difference between `service/` and `xlake/`? (One is HTTP, one is SDK - not obvious)
   - Where do new projects go?

## Decision

Reorganize the codebase around **semantic domains**, not languages. Each top-level directory should represent a clear product capability or concern.

### Guiding Principle

> **Organize by what the code does, not what language it's written in.**
>
> Python, TypeScript, Rust, etc. can live anywhere. The structure should make it easy to find code by its purpose.

## Target Structure

```
actbi/
├── web/                    # User interfaces
│   ├── admin/              # Admin dashboard
│   ├── bi/                 # BI dashboard
│   ├── xms/                # Prompt manager
│   └── shared/             # @actbi/shared (web utilities)
│
├── agents/                 # AI intelligence layer
│   ├── src/agents/
│   │   ├── intent_classifier/
│   │   ├── data_explorer/
│   │   ├── viz_designer/
│   │   └── tools/
│   └── tests/
│
├── evals/                  # Evaluation framework
│   ├── src/evals/
│   │   ├── framework/      # Experiment runner, storage, config
│   │   ├── datasets/       # JSONL test cases
│   │   ├── evaluators/     # Custom evaluation functions
│   │   ├── mocks/          # Test doubles
│   │   └── configs/        # YAML experiment configs
│   ├── tests/
│   └── notebooks/          # Eval notebooks
│
├── pipelines/              # Data ingestion (Dagster ETL)
│
├── xlake/                  # Semantic data layer (Python SDK)
│
├── service/                # HTTP API (FastAPI)
│
├── knowledge/              # RAG knowledge bases
│   └── data-viz-bible/     # Visualization guidance
│
├── lib/                    # Core shared libraries
│   ├── io/                 # exports shared.io
│   ├── data/               # exports shared.data
│   └── prompts/            # exports shared.prompts
│
├── notebooks/              # General Jupyter exploration
│
├── docs/                   # Documentation
│   ├── architecture/
│   ├── ux/
│   └── ADRs/
│
└── third_party/            # Vendored code
```

### Why Each Directory

| Directory | Purpose | Why Top-Level |
|-----------|---------|---------------|
| `web/` | User interfaces | Clear product layer |
| `agents/` | AI intelligence | Core product capability |
| `evals/` | Testing/evaluation | Cross-cutting, not tied to one system |
| `pipelines/` | Data ingestion | Distinct ETL concern |
| `xlake/` | Semantic data SDK | Core data access layer |
| `service/` | HTTP API | Clear API boundary |
| `knowledge/` | RAG content | Separate from code |
| `lib/` | Shared utilities | Cross-cutting libraries |
| `notebooks/` | Exploration | Development tool |
| `docs/` | Documentation | Project-wide |

## Changes Required

### Directory Moves

```
data/agents/                    -> agents/
data/agents/src/agents/evals/   -> evals/src/evals/
data/pipelines/                 -> pipelines/
data/xlake/                     -> xlake/
data/shared/                    -> lib/
data/analysis/                  -> notebooks/
data/analysis/notebooks/agents/ -> evals/notebooks/
data/docs/                      -> docs/architecture/
```

### Deletions

- `packages/viz/` - orphaned, not in any workspace
- `data/` - empty after moves

### Configuration Updates

**pyproject.toml workspace members:**
```toml
members = [
    "agents",
    "evals",
    "pipelines",
    "xlake",
    "lib/io",
    "lib/data",
    "lib/prompts",
    "notebooks",
    "service",
]
```

**Import changes:**
- `from agents.evals import ...` -> `from evals import ...`
- All other imports unchanged (package names stay the same)

## Consequences

### Positive

- **Clearer mental model** - Find code by what it does
- **Better onboarding** - New developers understand structure faster
- **Easier scaling** - Clear pattern for adding new domains
- **No language silos** - Python/TypeScript can coexist in any domain

### Negative

- **One-time migration cost** - Need to update imports, configs, docs
- **Git history** - Moves may complicate `git blame` (use `git log --follow`)

### Neutral

- **Python imports mostly unchanged** - Package names don't change, just locations
- **Build tools unaffected** - UV and pnpm workspaces still work

## Implementation Plan

### Phase 1: Cleanup
1. Delete `packages/viz/`
2. Consolidate `data/docs/` into `docs/architecture/`

### Phase 2: Reorganization
1. Move directories as specified above
2. Update `pyproject.toml` workspace members
3. Update `justfile` command paths
4. Update `AI_INSTRUCTIONS.md` hierarchy
5. Fix any broken imports (mainly evals)

### Phase 3: Feature Branch Merge
1. Cherry-pick `knowledge/data-viz-bible/` from feature/viz-agent
2. Cherry-pick xlake RAG enhancements
3. Keep main's eval framework (feature branch removed it)

## Notes

- **xlake is an SDK**, not HTTP. The `xlake/api/` directory is the public SDK surface, not endpoints. `service/` is the actual HTTP API.
- **lib/ vs web/shared/** - `lib/` contains Python packages (`shared.io`, `shared.data`), `web/shared/` contains TypeScript (`@actbi/shared`). Different ecosystems, no conflict.
- **Eval notebooks** belong with evals, not in general notebooks - keeps eval workflow self-contained.
