---
type: action-implementation
action: selection
chart-type: bullet_chart
aliases: [bullet graph, bullet bar, performance bar]
data-pattern: actual-vs-target
family: ranking
priority: P2
tags: [selection, bullet, performance, target, kpi]
---

# Selection: Bullet Chart

Shows a primary measure against a target, with qualitative ranges for context.

## When to Use

- **Actual vs. target comparison**: Performance against goal
- **KPI dashboards**: Compact performance display
- **Replacing gauges**: More information in less space
- **Multiple metrics side-by-side**: Compact comparison

### Data Pattern

- 1 PRIMARY MEASURE (actual value)
- 1 TARGET MEASURE (comparison marker)
- OPTIONAL: Qualitative ranges (poor/satisfactory/good)

### User Intent Signals

Queries that suggest bullet chart:
- "How are we doing against target..."
- "Performance vs. goal..."
- "Actual compared to budget..."
- "KPI status..."

## When NOT to Use

| Scenario | Problem | Use Instead |
|----------|---------|-------------|
| No target | Missing comparison point | Bar Chart, KPI Card |
| Showing trends | No temporal encoding | Line Chart with target |
| Many metrics (>10) | Gets overwhelming | Table with sparklines |
| Non-numeric comparison | Bullet needs numbers | Table |

## Data Requirements

| Field Role | Required | Description |
|------------|----------|-------------|
| MEASURE (primary) | Yes | Actual/current value |
| MEASURE (target) | Yes | Target/goal value |
| MEASURES (ranges) | No | Qualitative thresholds |

## Selection Decision

```
IF measures >= 2:
    AND hasTarget:
    AND intent == "performance" OR "vs target":
        → Bullet Chart
    
IF singleMetric AND hasTarget:
    AND wantCompact:
        → Bullet Chart (replaces gauge)
```

## Anatomy

```
┌─────────────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░│▓▓▓▓▓▓▓▓▓│█████████│
│░░░░░░░░░░░░░░░░░░░░░│▓▓▓▓▓▓▓▓▓│█████████│
│     Poor             │  OK     │  Good   │  ← Qualitative ranges
│░░░░░░░░░░░░░░░░░░░░░│▓▓▓▓▓▓▓▓▓│█████████│
│                ───── │         │         │  ← Target marker
│     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │         │         │  ← Actual bar
└─────────────────────────────────────────┘
```

## Variants

### Horizontal Bullet
Most common orientation.

### Vertical Bullet
For vertical dashboard layouts.

### Bullet without ranges
Just actual bar and target marker.

## Critical Rules

> **Target must be clearly marked.**

Use a distinct marker (line) that's easy to distinguish from the actual bar.

> **Keep ranges to 2-3.**

More than 3 qualitative ranges becomes confusing.

> **Label the metric.**

Without context, a bullet chart is meaningless.

## See Also

- [Selection Interface](./selection.md)
- [KPI Card](./selection-kpi-card.md) — Simpler single-metric display
- [Bar Chart](./selection-bar-chart-horizontal.md) — Without target comparison
