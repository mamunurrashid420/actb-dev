# React Graph Gallery - Upstream Tracking

**Source:** https://github.com/holtzy/react-graph-gallery
**Last Sync:** 2026-01-09
**Method:** git subtree

## About

This directory contains the upstream [react-graph-gallery](https://github.com/holtzy/react-graph-gallery) project by Yan Holtz. It is vendored here using git subtree to allow:

1. Full visibility for AI agents (Claude Code, Cursor)
2. Easy upstream syncing when new features are released
3. Clear separation between upstream code and our customizations

## Syncing with Upstream

To pull the latest changes from upstream:

```bash
git subtree pull --prefix=third_party/react-graph-gallery \
  https://github.com/holtzy/react-graph-gallery.git main --squash
```

## Our Customizations

Our customizations live in `packages/viz/`, NOT in this directory.

- **DO NOT** modify files in this directory directly
- Create wrappers/extensions in `packages/viz/` instead
- Import from `@actbi/viz`, not from `third_party/` directly

## Directory Structure

```
third_party/react-graph-gallery/   # Upstream code (don't modify)
packages/viz/                       # Our customizations
  src/
    custom/                         # New components we create
    index.ts                        # Re-exports upstream + custom
```
