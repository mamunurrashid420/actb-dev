# Prompts - Agent Reference

**For detailed explanations, see prompts/README.md (human docs)**

## Current State

**Scaffold only** - No prompts implemented yet.

## Planned Structure

```
prompts/
├── agents/                     # Agent prompt templates (versioned)
│   ├── supervisor/v1.yaml
│   ├── intent_classifier/v1.yaml
│   ├── query_builder/v1.yaml
│   ├── viz_designer/v1.yaml
│   └── data_interpreter/v1.yaml
└── contracts/
    └── xlake_reasoning.yaml    # Universal 100-word reasoning contract
```

## Design Principles

1. **Versioned prompts**: Use `v1.yaml`, `v2.yaml` suffixes for A/B testing
2. **Deterministic retrieval**: Same prompt ID always returns same content
3. **Agent-agnostic storage**: Prompts stored separately from agent implementation
4. **Universal contracts**: Shared reasoning patterns across all agents

## Future Schema (TBD)

When prompts are added, they should follow a consistent schema:

```yaml
name: <agent_name>
version: <version>
description: <brief_description>

system_prompt: |
  <multi-line prompt content>

# Optional sections
examples: []
constraints: []
output_format: {}
```

## Adding Prompts

When implementing prompts:

1. Create directory under `agents/` or `contracts/`
2. Use versioned filenames (`v1.yaml`)
3. Follow the schema conventions
4. Update this file with the new prompt reference

## Commands

```bash
# Sync workspace
uv sync

# Validate YAML (when implemented)
uv run python -m prompts.validate
```
