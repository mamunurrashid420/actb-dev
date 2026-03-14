# Welcome to actBI Data Pipeline

## What is actBI?

actBI is an AI-powered Business Intelligence platform that helps companies make better decisions by combining their internal business data with external economic, market, and regulatory data sources.

This data pipeline is the foundation of actBI—it fetches, processes, and organizes external data from sources like:

- **FRED** (Federal Reserve Economic Data) - US economic indicators
- **BLS** (Bureau of Labor Statistics) - Labor market data
- **World Bank** - International economic indicators for 20 countries
- **SEC EDGAR** - Public company filings and institutional holdings

The pipeline transforms this raw data into clean, well-structured datasets that both humans and AI systems can easily query and analyze.

## Why Does This Pipeline Exist?

Real businesses make real decisions based on data. A coffee company like Illy needs to understand:

- How are coffee commodity prices trending?
- Is consumer spending rising or falling in key markets?
- What are competitors reporting in their quarterly earnings?
- How do macroeconomic indicators correlate with sales?

This pipeline makes that analysis possible by:

1. **Automating data collection** - No manual downloads or spreadsheet updates
2. **Ensuring data quality** - Validation, transformation, and quality checks at every step
3. **Providing consistent structure** - Same format whether it's US GDP or Chinese inflation
4. **Enabling AI integration** - Metadata and structure optimized for LLM-powered tools

## How It Works

```
External APIs → Raw Data → Transformed Data → Published Data → Your Analysis
     ↓              ↓             ↓                  ↓              ↓
  FRED API      Parquet      Cleaned &          LLM-ready     DuckDB queries
  BLS API       files        validated          partitions    Jupyter notebooks
  World Bank               Partitioned          Semantic      Custom tools
  SEC EDGAR                by country           naming
```

The pipeline is built with **Dagster**, a modern data orchestration framework that provides:

- Clear visibility into data dependencies
- Automatic tracking of what's been materialized
- Scheduling and monitoring capabilities
- Rich metadata and observability

## Key Concepts

Before diving into the details, here are the core concepts you'll encounter:

- **Assets** - Datasets produced by the pipeline (e.g., GDP data, unemployment rates)
- **Partitions** - Logical slices of data (e.g., GDP data partitioned by country)
- **Resources** - Connections to external APIs (FRED API, World Bank API, etc.)
- **DAG (Directed Acyclic Graph)** - The dependency structure showing how data flows through the pipeline
- **Source/Intermediate/Leaf Nodes** - Different types of assets in the DAG

*Full explanations of these concepts are in [CONCEPTS.md](CONCEPTS.md).*

## Our Design Philosophy

### 1. Data Quality First

Businesses will make real decisions based on this data, so **reliability and accuracy are paramount**. We validate data at every boundary, log quality issues explicitly, and fail fast rather than propagate errors.

### 2. Flexible Architecture

Not all data needs the same number of transformation steps. Economic indicators might go directly from raw to published (2 layers), while SEC filings need parsing and enrichment (3 layers). Some future data sources might need 5+ layers.

**We build for today's use cases while designing for tomorrow's extensibility.**

### 3. AI Native

The pipeline is designed with AI integration in mind:
- Asset names match natural language queries
- Metadata includes "questions_answered" for LLM discovery
- Published data is pre-aggregated and narrative-ready

But we maintain engineering rigor—AI accelerates development, it doesn't replace good architecture.

### 4. Traditional but Lean

We follow proven patterns (validation, testing, observability) without over-engineering. No premature optimization, no unnecessary abstractions. Build what's needed, when it's needed.

## Documentation Guide

This documentation is organized to take you from beginner to contributor:

### Getting Started

1. **[GETTING_STARTED.md](GETTING_STARTED.md)** - Install and run the pipeline in 10 minutes
2. **[CONCEPTS.md](CONCEPTS.md)** - Understand the core building blocks

### Understanding the System

3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - How the pipeline is designed and why
4. **[DATA_SOURCES.md](DATA_SOURCES.md)** - What data we ingest from each source

### Working with the Pipeline

5. **[ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md)** - Step-by-step tutorial for adding new data
6. **[OPERATIONS.md](OPERATIONS.md)** - Running, scheduling, and monitoring
7. **[ANALYSIS.md](ANALYSIS.md)** - Querying and analyzing the data
8. **[TESTING.md](TESTING.md)** - Writing tests and ensuring quality

### Contributing

9. **[CONTRIBUTING.md](CONTRIBUTING.md)** - Code standards and PR process

## Quick Links

**Common tasks:**
- [Install and run the pipeline](GETTING_STARTED.md#installation)
- [Add a new FRED series](ADDING_DATA_SOURCES.md#adding-to-existing-sources)
- [Add a new company to SEC filings](DATA_SOURCES.md#sec-edgar)
- [Query data with DuckDB](ANALYSIS.md#duckdb-queries)
- [Run tests](TESTING.md#running-tests)
- [Troubleshoot issues](OPERATIONS.md#troubleshooting)

**Understanding concepts:**
- [What are partitions?](CONCEPTS.md#partitions)
- [What's the DAG?](CONCEPTS.md#the-dag)
- [Source vs Leaf nodes](CONCEPTS.md#asset-types)

## What's Next?

If you're **brand new to the project**, start with [GETTING_STARTED.md](GETTING_STARTED.md) to get the pipeline running on your machine.

If you **want to understand how it works**, read [CONCEPTS.md](CONCEPTS.md) next, then [ARCHITECTURE.md](ARCHITECTURE.md).

If you **want to add new data**, jump to [ADDING_DATA_SOURCES.md](ADDING_DATA_SOURCES.md) for a complete tutorial.

Welcome to actBI—let's build something useful together! 🚀
