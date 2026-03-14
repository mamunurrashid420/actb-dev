# XLake Store Architecture

> **Status**: Placeholder - Phase 2 of monorepo roadmap

This document will describe the XLake semantic layer and unified APIs.

## Planned Contents

From [MONOREPO_ROADMAP.md](../MONOREPO_ROADMAP.md):

- **Semantic Graph Model** - Logical graph over physical storage
- **Context Stores** - CoreContextStore, CustomerContextStore, etc.
- **Unified APIs** - semantic.search(), schema.get(), data.query(), context.get_active()
- **Connectors** - PostgreSQL, BigQuery, Trino integrations

## Key Architectural Constraints

1. Agents reason over logical graph, not physical storage paths
2. Minimal prompt, rich context - JSON context objects carry complexity
3. Multi-tenant isolation with row-level security
4. Unified semantics across all stores

## Implementation Location

When implemented, XLake will live in `xlake/` directory:

```
xlake/
├── src/xlake/
│   ├── core/           # Graph model, context building, entities
│   ├── stores/         # Store implementations
│   ├── connectors/     # Database connectors
│   └── api/            # Unified XLake API
```

## References

- [MONOREPO_ROADMAP.md](../MONOREPO_ROADMAP.md) - Migration phases
- [Agent-Architecture.md](Agent-Architecture.md) - Agents that consume XLake APIs
- [Data-Pipeline-Architecture.md](Data-Pipeline-Architecture.md) - Pipelines that publish to XLake
- [XLake-Store-Architecture-Full-Reference.md](../xlake/docs/XLake-Store-Architecture-Full-Reference.md) - All the design details and requirements for XLake

