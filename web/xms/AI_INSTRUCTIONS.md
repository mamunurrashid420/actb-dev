# AI Instructions - XMS (Prompt Management)

## Overview

XMS is a prompt management system for creating, organizing, and versioning AI prompts, snippets, and variables.

## Key Features

- **Prompts**: Create and manage AI prompt templates
- **Snippets**: Reusable text/code blocks
- **Variables**: Context variables for prompt interpolation
- **Workspaces**: Organized views for each content type

## Directory Structure

```
src/
├── app/
│   ├── api/              # API routes (prompts, snippets, variables)
│   └── page.tsx          # Main workspace UI
├── components/
│   ├── ui/               # shadcn/ui components
│   ├── workspaces/       # Workspace views
│   ├── PromptComposer.tsx
│   ├── SnippetEditor.tsx
│   └── VariableDrawer.tsx
├── services/             # Business logic
├── lib/
│   ├── store/            # Supabase store implementations
│   └── supabase/         # Supabase client
└── types/                # TypeScript definitions
```

## API Routes

| Route            | Purpose       |
| ---------------- | ------------- |
| `/api/prompts`   | Prompt CRUD   |
| `/api/snippets`  | Snippet CRUD  |
| `/api/variables` | Variable CRUD |

## Commands

```bash
just dev-xms    # Start dev server
just test-xms   # Run tests
just build-xms  # Production build
```

## Database

Uses **separate** Supabase project from admin/bi (prototype isolation).
Migrations in `web/xms/supabase/migrations/`.

Key tables: prompts, snippets, variables
