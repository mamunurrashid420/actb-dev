# XLake Architecture

See the monorepo-level document for the plan and constraints:

- `../../docs/XLake-Store-Architecture.md`

This project follows the prescribed structure:

```
src/xlake/
  core/         # Graph model, entities, context objects
  stores/       # Store abstractions and implementations
  connectors/   # DB connectors
  api/          # Public API surface
  models/       # Data types used by the system
```


