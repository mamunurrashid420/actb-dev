# Prompts - XMS Prompt Storage

Prompt storage and versioning system for actBI agents (Context Management System).

## Overview

This package provides centralized storage for agent prompts, enabling:

- **Version Control**: Prompts evolve without redeploying agents
- **A/B Testing**: Test prompt variations
- **Governance**: Centralized audit and governance
- **Deterministic Retrieval**: Consistent prompt access patterns

## Status

**Scaffold only** - No actual prompts implemented yet.

## Planned Structure

```
prompts/
├── agents/                     # Agent prompt templates
│   ├── supervisor/
│   │   └── v1.yaml
│   ├── intent_classifier/
│   │   └── v1.yaml
│   ├── query_builder/
│   │   └── v1.yaml
│   └── ...
└── contracts/                  # Agent instruction contracts
    └── xlake_reasoning.yaml    # Universal reasoning contract
```

## Design Rationale

From MONOREPO_ROADMAP.md:

> The Agent Architecture specifies a Context Management System (XMS) for prompt storage:
> - Prompts evolve without redeploying agents
> - Enables A/B testing of prompt versions
> - Centralizes governance and audit
> - Supports the "deterministic retrieval" principle

## Usage

TBD - Agents will load prompts at runtime when the agents/ package is implemented.

## Development

```bash
# From workspace root
uv sync

# Run tests (when implemented)
cd prompts
uv run pytest
```

## References

- [MONOREPO_ROADMAP.md](../MONOREPO_ROADMAP.md) - Target architecture
- [Agent-Architecture.md](../docs/Agent-Architecture.md) - Multi-agent system design (future)
