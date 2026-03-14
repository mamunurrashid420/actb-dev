"""Shared type definitions for agents and xlake.

These types should be the single source of truth for visualization-related
enumerations used across the ActBI platform.
"""

from typing import Literal

# ============================================================================
# Intent classification types (used by IntentClassifier agent)
# ============================================================================

# Task: High-level user intent category.
Task = Literal[
    "consult",  # Discovery: user wants to find or understand data
    "reflect",  # Analysis: user wants to analyze or interpret data
]

# Mode: Interaction style that determines agent behavior.
Mode = Literal[
    "reporter",  # Answers the question directly, factual
    "interpreter",  # Explains patterns, adds context and meaning
    "explorer",  # Extends beyond the question, suggests related signals
]

# Job: Specific workflow type to trigger downstream.
Job = Literal[
    "query",  # Run SQL, fetch data (most common)
    "visualize",  # Create or modify charts/graphs
    "discover",  # Find available data, explore what exists
    "schema_update",  # Modify data model or mappings
    "simulate",  # Run what-if scenarios
    "schedule",  # Set up recurring reports or alerts
    "navigate",  # Navigate to existing dashboard/chart/view
    "clarify",  # Query too vague, ask follow-up question
    "out_of_scope",  # Request outside platform capabilities
]

# ============================================================================
# Visualization types
# ============================================================================

# Chart types supported by ActBI visualization system.
# Source of truth: xlake/src/xlake/proto/actbi/v1/chart.proto (ChartType enum).
# This Literal mirrors the proto enum values for Python type-checking.
# Naming convention: lowercase snake_case, derived from data-viz-bible taxonomy.
ChartType = Literal[
    # P0 — Core (Always Available)
    "kpi_card",  # Single metric display
    "data_table",  # Tabular data display
    "bar_chart_vertical",  # Standard vertical bar chart
    "bar_chart_horizontal",  # Horizontal bar chart
    "line_chart",  # Time series, trends
    "area_chart",  # Stacked time series, part-of-whole over time
    "scatter_plot",  # Correlation, distribution
    "pie_chart",  # Pie chart (<=5 categories, standalone statement)
    "donut_chart",  # Donut chart (<=5 categories, dashboard component)
    # P1 — Extended
    "bar_chart_stacked",  # Stacked bars
    "bar_chart_grouped",  # Grouped/clustered bars
    "histogram",  # Distribution of continuous values
    "heatmap",  # 2D density, correlation matrices
    "treemap",  # Hierarchical part-of-whole
    "boxplot",  # Statistical distribution with quartiles
    "slope_chart",  # Before/after comparison
    # P2 — Specialized
    "waterfall_chart",  # Running totals, bridges
    "cohort_heatmap",  # Retention/cohort analysis
    "combo",  # Multiple chart types combined
    "violin_plot",  # Distribution + density
    "bullet_chart",  # Target vs actual comparison
    "funnel_chart",  # Conversion funnel
    "bubble_chart",  # Scatter with size encoding
    "lollipop_chart",  # Lightweight bar alternative
]

# Data shape categories for visualization selection.
DataShape = Literal[
    "temporal",  # Time-based data
    "categorical",  # Discrete categories
    "distribution",  # Continuous distribution
    "correlation",  # X-Y relationship
]

__all__ = ["ChartType", "DataShape", "Job", "Mode", "Task"]
