# AI Instructions - Web Applications

## Overview

The `web/` directory contains Next.js applications that form the user-facing part of actBI.

## Applications

| App       | Purpose                                      | Port | Status |
| --------- | -------------------------------------------- | ---- | ------ |
| **admin** | Tenant/user management, roles, permissions   | 3000 | Active |
| **xms**   | Prompt/snippet/variable management           | 3001 | Active |
| **bi**    | BI dashboard with chat, visualizations, i18n | 3002 | Active |

## Shared Patterns

### Technology Stack

- Next.js 15.5.x with App Router
- React 19.x
- TypeScript 5.x (strict mode)
- Tailwind CSS 4.x
- shadcn/ui components (Radix UI)
- Supabase for auth and database

### Directory Structure (per app)

```
<app>/
├── src/
│   ├── app/              # Next.js app router pages
│   │   ├── (protected)/  # Auth-required routes
│   │   ├── auth/         # Login/register
│   │   └── api/          # API routes
│   ├── components/       # React components
│   │   ├── ui/           # shadcn/ui components
│   │   └── <domain>/     # Domain-specific components
│   ├── hooks/            # Custom React hooks
│   ├── lib/              # Utilities
│   │   └── supabase/     # Supabase clients
│   ├── stores/           # Zustand stores
│   └── types/            # TypeScript types
├── supabase/
│   └── migrations/       # Database migrations
└── package.json
```

### State Management

- **Server state**: TanStack Query
- **Client state**: Zustand
- **Form state**: React Hook Form

### Authentication

- Supabase Auth with SSR
- Role-based access control (Admin, Creator, Viewer)
- Protected routes via middleware

## Commands

```bash
# Development
just dev-admin          # Start admin
just dev-xms            # Start xms
just dev-bi             # Start bi

# Testing
just test-js            # All JS tests
just test-admin         # Admin tests only
just test-xms           # XMS tests only
just test-bi            # BI tests only

# Building
just build-web          # Build all web apps
just build-admin        # Build admin only
just build-bi           # Build bi only
```

## Adding New Features

1. Create components in `src/components/<domain>/`
2. Add API routes in `src/app/api/<domain>/`
3. Use existing UI components from `src/components/ui/`
4. Follow existing patterns for auth, data fetching, forms
