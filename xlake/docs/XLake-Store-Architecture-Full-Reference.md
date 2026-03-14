# **XLAKE STORE ARCHITECTURE**

# **0\. Introduction**

The XLake is the semantic, contextual, and operational knowledge substrate that powers the ActBI platform. It serves as the foundation for how ActBI understands customer data, interprets business concepts, executes analytical reasoning, and accelerates dashboard interactions. Rather than being a traditional data lake or a BI warehouse, the XLake is a *context lake* — a layered system that organizes metadata, parsed schemas, extracted knowledge, embeddings, summaries, lineage, and cached analytical outputs into a unified structure accessible to ActBI agents.

The XLake bridges ActBI’s AI reasoning system with customer data systems. It stores the knowledge required for ActBI to interpret questions, generate correct queries, contextualize information, and construct meaningful dashboards or summaries. It also ensures that each customer’s world — their schemas, domain language, KPIs, documents, and dashboards — is modeled coherently and kept strictly isolated from other tenants, while still benefiting from the global expertise encoded in ActBI’s Core Context.

The architecture splits into two conceptual layers:

* **Core XLake (ActBI-controlled)**  
   Contains global business ontologies, domain expertise, external data knowledge, charting principles, and interpretation rules shared across all customers.

* **Customer XLake (Tenant-specific)**  
   Contains each customer's operational semantics, application state, extracted document knowledge, and cached analytical data.  
   Importantly, customer *raw data* is never stored in the XLake — it remains inside the customer’s own databases, exposed only through secure connectors and an optional federated query layer.

This separation enables the XLake to support multiple cloud providers, varying customer architectures, and strict compliance requirements. The result is a portable, extensible, multi-cloud semantic layer for ActBI that allows all agents to operate over a consistent, queryable, and interpretable domain model — regardless of where the underlying data physically resides.

# **1\. Logical Architecture of the ActBI XLake**

The ActBI XLake is the unified knowledge substrate that powers all AI reasoning, chart generation, dashboard storytelling, schema augmentation, and connector-based data access across customers. It is composed of two major categories of stores:

* **Core Stores** — global, ActBI-owned knowledge powering domain reasoning, external data, chart semantics, and AI intelligence.

* **Customer Stores** — isolated per-customer knowledge and data layers that support each tenant’s documents, schemas, internal data, and application logic.

Each store has an explicit purpose, its own storage technologies, and a clear role in how agents read, write, transform, or retrieve information.

The XLake is fully multi-tenant. Each store is logically partitioned so that customer-specific data is isolated while minimizing infrastructure duplication. For customers requiring private-cloud deployments, a single XLake deployment per cloud provider can serve multiple tenants via partitioning, without spinning up a full XLake instance for every customer.

Below is the logical architecture, divided into Core Stores and Customer Stores.

## **1.1 Core Stores (ActBI-Owned)**

These stores hold global, shared, ActBI-curated intelligence. They live exclusively in the ActBI cloud (GCP) and are never replicated into customer-owned clouds unless explicitly requested.

### 1.1.1 CoreContextStore

**Purpose:**  
 ActBI’s cross-industry, cross-domain semantic memory.  
 Contains business dictionaries, metric definitions, relationship ontologies, KPI templates, data modeling conventions, and chart-construction knowledge.

**Contents:**

* Domain knowledge: finance, supply chain, CRM, marketing, operations. Any knowledge we gather from expert documents, books, know-how we build over time etc. about the meaning of the domains to add specialized “intelligence”.  
* Metric ontologies: definitions, formulas, lineage templates.  
* Business relationships and definitions: “customer\_id joins sales.customer\_id”, “COGS → margin”, etc.  
* Visualization semantics: which chart types to use for which data patterns.  
* Schema augmentation logic: patterns discovered from multiple customers.  
* Charting and Dashboarding best practices.

**Storage Technologies:**

* **RAG (Qdrant Cloud on GCP)** — for embeddings, semantic retrieval.  
* **Postgres (Supabase)** — for structured metadata, relationships, definitions.  
* **Object Store (Supabase Storage/GCS)** — for files, dictionaries, reference sheets.

**Usage by agents:**

* Contextual grounding for any query.  
* Schema suggestion and metadata augmentation.  
* Automatic chart selection and narrative interpretation.  
* Intelligent join inference and KPI construction.

### 1.1.2 CoreExternalSourceStore

**Purpose:**  
 The global, processed repository of external data sources that enrich customer analyses without requiring customer ETL work.

**Contents:**

* Weather datasets  
* Macroeconomic trends  
* Market data, commodities, stocks  
* Industry benchmarks  
* Regulatory datasets (FDA, EFSA, ECHA)  
* Public financials

These datasets are pre-cleaned, restructured, and stored in OLAP format for fast joining with customer data.

**Storage Technologies:**

* **OLAP (ClickHouse Cloud / Tinybird)** — for structured external data queried at scale.  
* **RAG (Qdrant)** — for metadata, column meaning, data-source descriptions.  
* **Object Store (GCS)** — staged parquet files before ingestion.

**Usage by agents:**

* Auto-correlating customer KPIs with external signals.  
* Contextual “explorer-mode” insights (“margin dip aligns with storm disruptions”).  
* Augmenting dashboards with validated global indicators.  
* Forecasting and scenario modeling.

## **1.2 Customer Stores (Tenant-Isolated)**

All customer stores are logically separated per customer. Physically, they can live:

* In the shared ActBI GCP region (default SaaS mode)  
* In a customer-selected cloud provider (private-cloud mode)  
* In a hybrid model where connectors access customer-owned databases

A **single XLake deployment** in each cloud provider can serve many customers through partitioning, minimizing infrastructure duplication while maintaining strict isolation.

### 1.2.1 CustomerAppLogicStore

**Purpose:**  
 This is the source of truth for all operational data that the ActBI application itself uses for this customer’s workspace.

**Contents:**

* Users, roles, permissions  
* Dashboards, chart stacks, chart metadata  
* Filters, simulations, scenario chips  
* Conversations, versions, lineage metadata  
* App configuration, connector configs  
* KPI definitions created by the customer  
* Any agent-generated “business logic” content

**Storage Technologies:**

* **Relational DB (Postgres via Supabase)** — single DB with row-level tenant isolation.  
* **Optional Cache (Redis)** — accelerated access for app metadata or session state.

**Characteristics:**

* Multi-tenant partitioned by tenant ID.  
* High consistency, transactional integrity.  
* Backbone of all product functionality.

### 1.2.2 CustomerContextStore

**Purpose:**  
 Semantic understanding of the customer’s internal universe.  
 This is ActBI’s brain for each customer’s internal schema and business logic.

**Contents:**

* Parsed schemas from connected data sources (fields, tables, relationships).  
* Mappings between raw column names and business meanings.  
* Metadata extracted from unstructured customer documents.  
* Agent-generated corrections, clarifications, and augmentations.  
* Semantic embeddings of all customer metadata.

**Storage Technologies:**

* **RAG (Qdrant Cloud in customer-selected region)** — embeddings and semantic metadata.  
* **Object Store** — raw schema files, JSON descriptions.  
* **Postgres** — structured mapping tables.

**Characteristics:**

* Evolves continuously as the customer adds new data sources.  
* Drives the AI’s ability to translate NL → SQL accurately.

### 1.2.3 CustomerDocStore

**Purpose:**  
 A pipeline for transforming the customer’s unstructured documents into structured data \+ metadata.

**Contents:**

* Raw customer documents (PDFs, Excel, drive folders, etc.).
* Simple metadata related to lineage/provenance of the file:
  * Author
  * Title
  * Category
  * Page count
  * Creation timestamps
  * Version
  * Source: manual upload, external store URI, etc.
  * Tags


**Two parallel streams emerge from each document:**

1. **Actual Data** → structured → stored as parquet → fed into OLAP.  
2. **Metadata** → descriptive context → embedded into RAG.

**Storage Technologies:**

* **Object Store** — original documents and provenance metadata.

**Characteristics:**

* Enables dashboards and queries on information extracted from documents without manual ETL.  
* Enables semantic reasoning about business rules (“price\_per\_kg rises after storms”).

### 1.2.4 CustomerChartStore

**Purpose:**  
 Serves high-performance chart-ready data to the ActBI UI.

**Contents:**

* Cached data slices needed for charts and dashboards.  
* Materialized datasets created by agents.  
* KPI time series and aggregated metrics.  
* Pre-computed trendlines, anomalies, what-if projections.

**Storage Technologies:**

* **OLAP (ClickHouse / Tinybird)** — high-speed analytical queries.  
* **Relational DB** — chart descriptors and lineage.  
* **(Optional) Redis** — caching of frequently-accessed chart data.

**Characteristics:**

* The performance-critical layer of ActBI.  
* Accelerates dashboard loading by avoiding re-querying OLAP for every render.  
* Supports scenario overlays and multi-view comparisons.

### 1.2.5 CustomerDataLakeStore

**Purpose:**  
 A unified, queryable interface over the customer’s internal databases, warehouses, or lakes — without forcing replication. Essentially a thin layer using our connectors.
 However, we also add structured data that is extracted from unstructured documents to make them available for data joining queries. Same for data that is “simulated”.

This is how ActBI connects to:

* Customer Postgres  
* Customer BigQuery  
* Customer Snowflake  
* Customer Redshift  
* Customer parquet lakes  
* Any JDBC-enabled DB

**Storage / Connector Layer:**

* **Trino (e.g., Starburst.io SaaS)** — federated query engine across heterogeneous sources.  
* **ActBI Connectors** — custom-built connectors for PostgreSQL, BigQuery, SaaS APIs, vector stores, etc.
* **OLAP (ClickHouse / Tinybird)** — to host extracted and simulated data.

**Characteristics:**

* Thin wrapper that translates NL → SQL → execution across customer sources.  
* No need to import customer internal tables unless the customer wants ActBI-managed storage.  
* Federated joins made possible across multiple sources.  
* Clear separation between “customer data ownership” and ActBI XLake intelligence.
* Integrated structured data store across customer DBs, Extracted File data, Simulated Data.

## **1.3 Architectural Principles Across All Stores**

### 1.3.1 Tenant Isolation Without Duplication

* A single XLake deployment per cloud provider (GCP, AWS, Azure) can support many customers.  
* Isolation achieved using:  
  * Row-Level Security (Postgres)  
  * Namespace / collection separation (Qdrant)  
  * Tenant IDs in OLAP datasets  
  * Bucket-per-tenant or prefix-only isolation (Object Store)  
  * Connector-level credential boundaries (Trino catalogs)

This minimizes cost while satisfying enterprise security.

### 1.3.2 Data Gravity and Deployment Flexibility

Depending on where customer data lives:

* **SaaS mode:** all XLake components run in GCP; connectors fetch from customer DBs.  
* **Private-cloud mode:** XLake deployed in customer’s preferred cloud region; only Core Stores stay in GCP.  
* **Hybrid mode:** CustomerDataLakeStore lives in customer cloud, while CustomerContextStore and CustomerChartStore stay in GCP.

### 1.3.3 Unified Semantics Across Stores

The following concepts are shared across all stores:

* Schema vocabulary  
* Business relationships  
* Data lineage style  
* Dashboard/story structure  
* Metric templates and KPI definitions  
* Query translation logic

This ensures consistent reasoning, interpretation, and visualization across all customers and all data types.

### 1.3.4 Agent-Oriented Access Pattern

All ActBI agents — Explainer, Explorer, Augmenter, Importer — access XLake through:

1. **Semantic queries** → RAG  
2. **Logical data queries** → SQL templates via CustomerDataLakeStore  
3. **Analytical queries** → OLAP  
4. **Document access** → CustomerDocStore  
5. **Application state** → CustomerAppLogicStore  
6. **Chart rendering data** → CustomerChartStore  
7. **Domain ontology** → CoreContextStore  
8. **External reasoning** → CoreExternalSourceStore

Agents always operate on a unified logical layer, regardless of where data physically lives. We expose to agents a unified XLake API for all their needs as described later in this document.

# **2\. Physical Architecture**

The XLake runs as a distributed, multi-cloud system composed of storage engines, compute pipelines, and connector runtimes that together implement the logical stores described in Section 1\. Its physical design supports a wide range of customer deployment requirements, from fully hosted SaaS to private-cloud installations inside a customer’s infrastructure. The architecture emphasizes strong tenant isolation, minimal duplication of resources, predictable performance, and consistent semantics across cloud providers.

The physical layer must satisfy five constraints simultaneously:

1. **Multi-tenancy** without leaking data or metadata.  
2. **Multi-cloud flexibility**, allowing customer-specific deployments.  
3. **Performance** across workloads involving OLAP, RAG, connectors, and application metadata.  
4. **Minimal duplication**, achieving isolation without spinning up full stacks per tenant.  
5. **Unified access** so agents interact with a consistent abstraction regardless of where data physically resides.

At a high level, the XLake consists of:

* Physical storage engines  
* Compute engines for ingestion and embedding  
* Connector runtimes for federated queries  
* Network and security layers that define the trust boundaries  
* Deployment topologies that vary by cloud and customer type

The following sections describe each of these in detail.

## **2.1 Storage Engines and Their Role**

The XLake uses four primary storage technologies and one caching layer. Each logical store maps to a combination of these engines.

### 2.1.1 Relational Engine — Postgres (Supabase or Cloud Equivalent)

Used for application metadata, lineage, dashboards, chart descriptors, connector configuration, tenant configuration, and structured mappings.

**Characteristics:**

* Strong consistency  
* Transactional operations  
* Row-Level Security (RLS) for tenant isolation  
* Replication or read replicas for better read throughput

**Mapping:**  
 Backs the **CustomerAppLogicStore**, and parts of **CustomerContextStore** and **CustomerChartStore**.

### 2.1.2 Vector Engine — Qdrant

Used for storing embeddings and semantic metadata for both customer-specific and global (ActBI) knowledge.

**Characteristics:**

* High-throughput vector search  
* Support for namespaces or collections for strict tenant separation  
* Qdrant Cloud deployable in AWS, Azure, and GCP  
* Works well with multi-cloud architectures

**Mapping:**  
 Backs the **CustomerContextStore**, **CustomerDocStore** (for metadata), and the **CoreContextStore** and **CoreExternalSourceStore**.

### 2.1.3 OLAP Engine — ClickHouse or Tinybird

Used for large-scale analytical workloads, parquet-backed datasets, extracted document tables, and fast dashboard computations.

**Characteristics:**

* Columnar storage optimized for analytics  
* Fast aggregations and group-bys  
* Supports external table joins (including federated sources when needed)  
* Scalable, cost-efficient storage model

**Mapping:**  
 Backs the **CustomerDocStore** (extracted data), **CustomerChartStore**, and **CoreExternalSourceStore**.

### 2.1.4 Object Storage — S3, GCS, Azure Blob, or Supabase Storage

Used for long-term file storage, raw documents, parquet files before OLAP ingestion, and JSON metadata snapshots.

**Characteristics:**

* Cloud-native, scalable, and cost-efficient  
* Folder or prefix-based tenant isolation  
* Versioning and lifecycle management for cost control

**Mapping:**  
 Backs the **CustomerDocStore**, **CustomerContextStore**, **CoreContextStore**, and **CoreExternalSourceStore**.

### 2.1.5 Cache Layer — Redis

Used for storing precomputed chart datasets, intermediate results, and any ephemeral data requiring millisecond access speeds.

**Characteristics:**

* Low-latency key–value access  
* Suitable for dashboard warmups and user-facing interactions  
* Allows cache invalidation policies and TTLs

**Mapping:**  
 Backs the **CustomerChartStore** and certain parts of the **CustomerAppLogicStore**.

## **2.2 Connector Layer and Customer Data Access**

The **CustomerDataLakeStore** sits on top of the customer’s operational databases. It does not persist data inside ActBI; instead, it relies on connectors and federated query engines to access customer data efficiently.

### 2.2.1 ActBI Connectors

ActBI provides cloud-agnostic connectors for:

* PostgreSQL  
* BigQuery  
* Snowflake  
* Redshift  
* Data lakes (parquet or delta-based lakes)  
* SaaS APIs (via HTTP-based connectors)

Connectors handle:

* Authentication  
* Schema reflection  
* Sampling  
* Query execution  
* Rate limiting  
* Pushdown optimization

### 2.2.2 Federated SQL via Trino (Starburst.io)

In more advanced deployments, ActBI can route customer queries through a managed Trino runtime (Starburst.io), supporting:

* SQL queries across multiple sources  
* Schema virtualization  
* Cross-system joins (e.g., BigQuery \+ PostgreSQL)  
* Pushdown execution patterns for performance  
* Secure per-tenant catalogs and credentials

Trino serves as the “query plane” for customer data without requiring replication or ingestion.

## **2.3 Deployment Topologies**

The XLake supports three distinct deployment configurations.

### 2.3.1 Standard SaaS Deployment (Default)

All XLake components run in ActBI’s GCP infrastructure:

* Qdrant (ActBI-controlled namespaces)  
* Supabase Postgres  
* ClickHouse/Tinybird  
* GCS for storage  
* Managed Redis  
* Connectors reaching into customer-owned databases

This provides the fastest time to value and simplest operations model.

### 2.3.2 Private-Cloud Deployment (Customer-Hosted XLake)

Required by enterprises with strict compliance or sovereignty constraints.

* XLake deployed inside the customer’s cloud (AWS/Azure/GCP)  
* ActBI agents run inside the same VPC or VNet  
* CustomerDataLakeStore has local, low-latency access  
* Only the **Core Stores** remain in the ActBI GCP region

In this model, a *single* XLake instance inside the customer cloud can serve multiple tenants belonging to the same enterprise group.

### 2.3.3 Hybrid Deployment

A combination of the above:

* CustomerDataLakeStore runs in the customer cloud for data-gravity reasons  
* XLake core components (RAG, OLAP, relational store) stay in ActBI GCP  
* Connectors reach back into the customer VPC  
* Cached datasets and semantic metadata remain centralized

This balances operational simplicity with data locality needs.

## **2.4 Multi-Tenancy and Isolation Model**

Multi-tenancy is enforced at every layer of the physical system:

### **2.4.1 Postgres**

* Row-Level Security (RLS)  
* Tenant-specific schemas if required  
* Tenant audit tables for lineage and queries

### **2.4.2 Qdrant**

* Separate collections or named vectors per tenant  
* Optional shard-level isolation  
* Per-tenant encryption keys

### **2.4.3 OLAP**

* Tenant-specific tables or partitions  
* Catalog-level separation for ClickHouse/Tinybird

### **2.4.4 Object Store**

* Per-tenant prefix or bucket  
* IAM-based isolation  
* Optional encryption key per customer

### **2.4.5 Connectors**

* Separate credentials per tenant  
* Per-tenant catalog configuration for Trino  
* No shared data paths between customers

## **2.5 Compute and Pipeline Orchestration**

Compute layers handle document parsing, schema inference, metadata extraction, embeddings, OLAP ingestion, and chart materialization.

**Compute roles include:**

* Document parsing workers  
* Schema inference workers  
* Embedding generation pipelines  
* Data extraction and normalization processors  
* OLAP ingestion replicas  
* Dashboard cache warmers  
* RAG indexing workers

These pipelines run in parallel and scale independently.

## **2.6 Networking and Security**

Security boundaries are enforced through:

* VPC or VNet isolation  
* Private networking for connectors  
* Encrypted connections (TLS everywhere)  
* No inbound firewall rules except from ActBI-controlled services  
* Optionally: customer-to-ActBI VPN or private link

Credentials for customer data stores are stored encrypted and scoped to the CustomerAppLogicStore for each tenant.

## **2.7 Cost Optimization and Scaling**

Cost is controlled through:

* Multi-tenant shared deployments per cloud provider  
* Hot/cold storage tiering for object stores  
* Materialized views to reduce repetitive OLAP queries  
* Embedding batching for cost-effective vector indexing  
* On-demand scaling for OLAP and connector compute

The architecture scales horizontally and supports large customer volumes without rearchitecting.

# **3\. Cross-Cutting Concerns**

Cross-cutting concerns define the non-functional, system-wide properties that apply to every store, pipeline, and connector in the XLake. These concerns ensure that the architecture behaves predictably across customers, clouds, and deployment modes. They include semantics, reliability, isolation, security, performance, observability, cost efficiency, and operational continuity.

The XLake integrates multiple storage engines, federated query layers, and ingestion pipelines. Because these components interact heavily with each other and with customers’ data stores, cross-cutting concerns must be explicitly defined and consistently implemented to prevent architectural drift or inconsistent semantics between tenants.

## **3.1 Versioning and Lineage**

Versioning is a foundational requirement for the XLake because schemas, documents, KPIs, dashboards, and extracted metadata all evolve over time. Without explicit version control, agents would operate on stale or ambiguous context, leading to incorrect analyses or charts.

### 3.1.1 Schema Versioning

* Each connected source has a versioned schema representation inside the CustomerContextStore.  
* Schema diffs trigger re-indexing and optional updates to downstream embeddings.  
* Version histories are retained to allow agents to interpret past dashboards or conversations accurately.

### 3.1.2 KPI and Metric Versioning

* KPIs defined by customers or inferred from documents are versioned to preserve historical meaning.  
* Changes in formulas update the corresponding semantic embeddings and OLAP materializations.

### 3.1.3 Dashboard and Chart Versioning

* Changes to charts, filters, transformations, and stacks generate new versions that are linked to conversations and lineage.  
* Agents can explain differences or regressions between versions.  
* The conversation artifact and the chart/stack/dashboard artifacts are linked and remembered together to show the cause and effect of each user change.

### 3.1.4 Document and Metadata Versioning

* Every document ingested from the CustomerDocStore maintains:  
  * Raw version  
  * Extracted structured data version  
  * Extracted metadata version  
* These versions allow for explainable transformations between unstructured → structured content.

### 3.1.5 Lineage as a First-Class Concept

* Lineage connects schemas, KPIs, documents, transformations, queries, and chart materials.  
* It is stored partly in relational form (CustomerAppLogicStore) and partly in semantic form (CustomerContextStore).

## **3.2 Performance Guarantees**

Performance considerations impact every interaction between agents, dashboards, and customer data sources. The XLake must operate efficiently even when querying large internal datasets or executing complex cross-source analyses.

### 3.2.1 Query Pushdown

* Wherever possible, computations are pushed to the customer’s source systems via the CustomerDataLakeStore.  
* Trino-backed federated queries (Starburst) preserve performance across heterogeneous data systems.

### 3.2.2 OLAP Materialization

* Frequently accessed or computationally heavy queries are materialized inside the OLAP engine.  
* CustomerChartStore caches reduce reliance on repeated OLAP scans.

### 3.2.3 Low-Latency Semantic Search

* RAG queries against Qdrant must remain low-latency even under load.  
* Vector indexes are partitioned per tenant to avoid cross-customer contention.

### 3.2.4 Precomputation and Cache Warmups

* Dashboard warmups generate cached data upon user login or scheduled refresh.  
* Agents can precompute common analyses to reduce chart load times.

### 3.2.5 Scaling Policies

* OLAP clusters scale horizontally under analytical load.  
* Embedding pipelines scale independently of application traffic.  
* Redis autoscaling maintains near-constant latency for chart data.

## **3.3 Tenant Isolation and Multi-Tenancy**

Isolation guarantees are crucial for a multi-tenant AI analytics platform where customer data remains highly sensitive.

### 3.3.1 Logical and Physical Isolation

Isolation is enforced on four levels:

1. **Access isolation** — credentials, Trino catalogs, and connector configurations are tenant-scoped.  
2. **Data isolation** — Postgres RLS, Qdrant collections, OLAP table partitioning, and per-tenant object store prefixes.  
3. **Compute isolation** — optional per-tenant Trino engines, OLAP clusters, or private-cloud deployments.  
4. **Semantic isolation** — embeddings, metadata, and document extractions are never mixed between tenants.

### 3.3.2 Shared Infrastructure With Partitioning

A single deployment per cloud region can safely serve many customers:

* Qdrant collection-per-tenant  
* Postgres row-level security  
* Tenant partitions in OLAP tables  
* Object store namespace isolation

This minimizes operational cost while maintaining strong boundaries.

### **3.3.3 Customer-Owned Environments**

When customers demand private-cloud installations:

* Customer stores run entirely in the customer's cloud.  
* CoreContextStore and CoreExternalSourceStore remain in ActBI GCP unless mirrored by request.  
* Networking is secured using VPC/VNet peering or private endpoints.

## **3.4 Security and Compliance**

Security requirements must hold across clouds, databases, and connectors.

### 3.4.1 Encryption

* All data at rest is encrypted via the storage provider (Postgres, Qdrant, ClickHouse, object store).  
* Data in transit uses TLS for every connection: connectors, Trino, OLAP clients, and agent APIs.

### 3.4.2 Credential Isolation

* Each tenant’s connector credentials are stored privately and encrypted.  
* Trino catalogs are configured with per-tenant restriction policies.  
* ActBI employees see only masked or scoped credentials depending on role.

### 3.4.3 Governance and Access Control

* RBAC governs:  
  * dashboard access  
  * connector configuration  
  * data mapping  
  * KPI creation  
  * document ingestion  
* Audit trails log queries executed through connectors, OLAP, or Trino.

### 3.4.4 Compliance Requirements

The architecture supports:

* SOC 2  
* GDPR  
* Data residency requirements  
* Optional data-processing agreements per enterprise tenant

Since customer data remains largely in the customer’s data stores, compliance is streamlined.

## **3.5 Observability and Monitoring**

Observability ensures that ingestion pipelines, connectors, and analytical engines operate predictably.

### 3.5.1 Metrics

The system tracks:

* Connector health and latency  
* OLAP query performance  
* Cache hit/miss ratios  
* RAG query latency  
* Schema drift and extraction quality  
* Document ingestion throughput

### 3.5.2 Logging

* Application logs  
* Connector logs  
* Document ingestion and parsing logs  
* Query logs from OLAP and Trino  
* API-level logs for agent interactions  
* Authentication and permission audit logs

### 3.5.3 Distributed Tracing

Tracing spans ingestion → RAG indexing → OLAP materialization → dashboard rendering.  
 This is essential for diagnosing bottlenecks in multi-cloud deployments.

## **3.6 Cost Optimization**

Cost management is embedded in the storage and compute architecture.

### 3.6.1 Hot/Cold Tiering

* Recent or frequently used documents stay in hot storage; older ones move to cheaper cold tiers.  
* OLAP tables may be split into hot partitions and long-term archives.

### 3.6.2 Shared Multi-Tenant Clusters

* Qdrant, ClickHouse/Tinybird, and Redis operate in multi-tenant mode with strict partitioning.  
* This avoids per-tenant cluster duplication while maintaining isolation.

### 3.6.3 Materialized Views Instead of Repeated Queries

* Agents materialize heavy or frequently executed analytical queries.  
* Reduces OLAP scan costs and cloud egress charges.

### 3.6.4 Embedding Batching

* Documents and metadata embeddings are processed in batches to reduce LLM usage.  
* Embedding refreshes only occur on detected schema or metadata changes.

### 3.6.5 Autoscaling

* OLAP clusters and compute pipelines scale according to load.  
* Redis and connector runtimes scale independently to maintain responsiveness without unnecessary idle cost.

## **3.7 Operational Continuity**

Operational continuity ensures that ingestion, analysis, and dashboarding remain stable even under failures or cloud service disruption.

### 3.7.1 Backup and Recovery

* Postgres backups with PITR (Point-In-Time Recovery)  
* ClickHouse snapshot backups  
* Qdrant backups for vector indexes  
* Object store versioning  
* Automated disaster recovery rotation

### 3.7.2 Resilience

* Connectors retry strategy with exponential backoff  
* Multi-zone OLAP and Postgres deployments  
* Failover replicas for Redis  
* Graceful degradation: if an external source is unavailable, cached insights remain accessible

### 3.7.3 Deployment Automation

* Infrastructure-as-code for all XLake components  
* Safe migrations for schema changes  
* Automated scaling and health checks

## **3.8 Consistency and Semantic Coherence**

The architecture must ensure consistency of meaning across stores.

### 3.8.1 Unified Naming Conventions

* Columns, metrics, KPIs, and entities use standardized naming across all stores.  
* Paralysis due to inconsistent naming is avoided by mapping raw names → business concepts in the CustomerContextStore.

### 3.8.2 Embedding Consistency

* Core and Customer embeddings use the same embedding model family to ensure semantic compatibility.  
* Embeddings are versioned and tagged with model identifiers.

### 3.8.3 Semantic Drift Management

* If customer datasets evolve significantly, embeddings and metadata are refreshed.  
* Drifts are detected using schema diffing and vector similarity changes.  
* Agents are notified of drift to avoid inaccurate interpretations.

# **4\. Data Models and Graph Schema**

The XLake organizes knowledge in both **structured** and **semantic** forms. Structured data models cover relational tables, OLAP-backed datasets, parquet files, document extractions, and connector metadata. Semantic data models capture business meaning, relationships, lineage, and embeddings. Together, these models provide agents with a unified representation of the customer’s world, supporting accurate query generation, interpretability, and storytelling.

This section describes the conceptual data model, the graph schema that connects different types of knowledge, and the specific entities and relationships present in each of the XLake’s logical stores.

## **4.1 Overview of the XLake Data Model**

The XLake data model blends four modeling layers:

1. **Relational models** — application metadata and structured lineage.  
2. **Columnar and parquet models** — analytical datasets and materialized views.  
3. **Document and file models** — raw documents and extracted content.  
4. **Semantic graph models** — conceptual nodes, embeddings, and relationships.

The semantic model is the backbone that allows agents to navigate between:

* user questions and underlying data fields  
* KPI definitions and the fields they depend on  
* extracted document statements and business concepts  
* dashboard elements and their corresponding datasets  
* metrics and external signals that influence them

However, this graph is **logical**, not stored in a single graph database. Instead, relationships are **materialized across multiple physical stores**:

* **Postgres** — structured lineage, metadata tables, schema definitions, dashboard mappings, KPI formulas.  
* **Qdrant** — embeddings and semantic metadata, encoding similarity and meaning.  
* **OLAP (ClickHouse/Tinybird)** — dataset provenance, transformation outputs, materialized analytical tables.  
* **Object storage** — document structures, extracted tables, and metadata files linking raw text to fields or KPIs.

Taken together, these stores form a **virtualized semantic graph**.  
 ActBI agents are instructed to reconstruct logical relationships by querying the appropriate store(s), enabling them to reason over the XLake as a unified graph despite its distributed physical structure.

## **4.2 Semantic Graph Schema**

The semantic layer is modeled conceptually as a graph of **nodes** and **edges**. Nodes represent entities such as fields, tables, metrics, documents, chunks, dashboards, and insights. Edges represent relationships between them—structural, semantic, causal, analytical, or lineage-based.

Although the graph is logical, each node and edge maps to concrete storage artifacts (row records, metadata entries, vector embeddings, parquet files, etc.).

### 4.2.1 Node Types

Nodes represent the discrete entities that make up the customer and core knowledge models. Most nodes have both structured attributes and semantic embeddings.

#### **A. Data Nodes**

These represent structural elements in customer data environments.

* **Table**  
  * table name, source system, data domain  
  * physical metadata such as column count  
* **Column / Field**  
  * data type, units, classifications  
  * semantic meaning and embedding vectors  
* **Dataset (Parquet/OLAP)**  
  * derived from documents or materialized computations  
  * partitioning and lineage metadata

#### **B. Business Concept Nodes**

Represent business semantics.

* KPIs and metric definitions  
* Business entities (Customer, Product, Region, Facility)  
* Domain constructs (Margin, Lead Time, Forecast Error)  
* Ontology terms and synonyms  
* Template metrics from CoreContextStore

These nodes exist both in **CoreContextStore** (global definitions) and **CustomerContextStore** (tenant-specific refinements).

#### **C. Document Nodes**

Represent all unstructured content and its derived components.

* Raw document nodes  
* Document chunk nodes  
* Extracted Type A data (tables)  
* Extracted Type B metadata (descriptive statements)

Each chunk is indexed with an embedding and linked back to its original file.

#### **D. Dashboard and Chart Nodes**

Represent analytical artifacts that power the ActBI user interface.

* Charts  
* ChartStacks  
* Dashboards  
* Chart descriptors, filters, and scenarios  
* Insights or narratives generated by agents

These nodes combine structured descriptors with semantic embeddings.

#### **E. External Signal Nodes**

Represent global signals from CoreExternalSourceStore.

* Weather events  
* Commodity movements  
* Macroeconomic indicators  
* Regulatory changes  
* Industry benchmarks

They enrich customer analyses with contextual correlations.

### **4.2.2 Edge Types**

Edges formalize how nodes relate to one another. We can use these names to formalize instructions we give to agents.  
 They are stored either:

* structurally (in Postgres metadata tables),  
* semantically (as metadata in Qdrant), or  
* procedurally (within OLAP and document extraction lineage).

#### **A. Structural Relationships**

* **table\_has\_column →** connects tables to their fields  
* **dataset\_derived\_from →** extraction lineage from documents  
* **document\_contains →** links raw documents to chunk nodes  
* **document\_generates\_metadata →** links extracted metadata to documents

#### **B. Semantic Relationships**

* **field\_maps\_to\_concept →** maps fields to business concepts  
* **concept\_refines →** relates customer concepts to global Core concepts  
* **kpi\_uses\_field →** links KPI formulas to their input fields  
* **kpi\_derived\_from\_kpi →** metric-to-metric lineage

#### **C. Causal and Behavioral Relationships**

* **concept\_correlates\_with\_signal →** relationships with weather, market, or external forces  
* **metadata\_describes\_behavior →** statements describing field behavior  
* **scenario\_changes\_metric →** simulations and what-if results

#### **D. Analytical Relationships**

* **chart\_represents\_field →** chart → field associations  
* **chart\_derived\_from\_dataset →** chart → materialized dataset lineage  
* **dashboard\_contains\_chart →** hierarchical structure  
* **insight\_relates\_to\_metric →** narrative → metric mapping  
* **insight\_relates\_to\_event →** enriched narrative → external signal mapping

#### **E. Lineage Relationships**

* **query\_uses\_field →** SQL query → field mapping  
* **chart\_generated\_from\_query →** chart lineage  
* **dashboard\_version\_of →** version lineage  
* **document\_version\_of →** version lineage for document and extraction outputs

These edges empower deep traceability and explainability.

## **4.3 Structured Data Model: Relational Schema**

The relational schema resides in the CustomerAppLogicStore and stores deterministic application and structural metadata.

### 4.3.1 Application Entities

* Users, roles, permissions  
* Dashboards, charts, chart stacks  
* Filters, scenarios, saved analyses  
* Connector configurations

### 4.3.2 Lineage Tables

* Chart → query → fields  
* Dashboard → charts  
* KPI → formula → fields  
* Connector → tables  
* Document → extracted tables

### 4.3.3 Metadata Tables

* KPI definitions and versions  
* Semantic mappings (field → business term)  
* Document registry and extraction metadata  
* Query templates and transformation patterns

These tables complement the semantic layer with deterministic structure.

## **4.4 OLAP Data Model**

Analytical storage in ClickHouse or Tinybird is used for fast querying of:

* extracted Type A data (actual data from documents)  
* materialized analytical datasets  
* external datasets

### 4.4.1 Extracted Data Tables

* Schema-inferred tables from documents  
* Parquet-derived column types  
* Partitioning based on tenant, date, or domain

### 4.4.2 Materialized View Tables

* KPI aggregates  
* Join results  
* Trendline calculations  
* Scenario simulations

### 4.4.3 External Data Tables

* Weather, climate, market data  
* Benchmarks  
* Regulatory datasets

These support agent queries and high-speed dashboard loading.

## **4.5 Document Model and Extraction Outputs**

### 4.5.1 Raw Document Metadata

* File identifiers and storage paths  
* Version history  
* Source type (upload, shared drive, connector)  
* Ingestion timestamps

### 4.5.2 Extracted Data Structures (Type A)

* Structured tables extracted from documents  
* Stored as parquet, ingested into OLAP  
* Linked back to documents through lineage metadata

### 4.5.3 Extracted Metadata Structures (Type B)

* Sentences describing behavior or meaning  
  * e.g., “price\_per\_kg increases after storms”  
* Embedded semantically and indexed in RAG  
* Linked to the relevant fields, KPIs, or tables

## **4.6 Embedding Models and Vector Schema**

The vector layer indexes entities that require semantic search:

* Fields  
* Tables  
* KPI definitions  
* Concepts  
* Document chunks  
* Metadata sentences  
* Chart descriptions  
* Dashboard summaries  
* External signals

Each embedding entry includes:

* vector embedding  
* model version  
* node ID  
* store type (customer or core)  
* tenant ID  
* timestamp and semantic tags

Embeddings form the core of semantic retrieval for agents.

## **4.7 Consistency Rules for the Data Model**

### 4.7.1 Bidirectional Mapping

Every structured item (table, KPI, chart, document extract) must map to a corresponding semantic node when relevant.

### 4.7.2 Model Version Awareness

All embeddings and relationships are tagged with the model version used to generate them.

### 4.7.3 Namespacing

All nodes, embeddings, and metadata entries are scoped by:

* tenant  
* store type  
* entity type  
* version

### 4.7.4 Immutability

Historical data—including document extractions, KPI versions, and schema snapshots—is immutable once stored.

## **4.8 Agent Interaction With the Data Model**

Agents operate over the XLake data model through three unified behaviors:

### **4.8.1 Semantic Reasoning**

Agents query the semantic graph to understand meaning, resolve ambiguity, find relationships, and interpret user questions.

### **4.8.2 Query Generation**

Agents traverse the structural and semantic layers:

question → concept → field → connector → SQL template → dataset

This flow depends heavily on the distributed graph model.

### **4.8.3 Interpretation and Storytelling**

Agents generate insights by weaving together:

* results from OLAP  
* metadata from CustomerDocStore  
* relationships from CustomerContextStore  
* external signals from CoreExternalSourceStore  
* semantic definitions from CoreContextStore

This unified access pattern allows agents to reason consistently across all stores, even though the data model is physically distributed.

[Appendix 1](#appendix-1:-protocol-buffer-schema-and-diff-rules) has a detailed data model for Charts and Conversations to feed our UI using a protocol buffer design to make chart diffs easy to understand for agents.

[Appendix 2](#appendix-2:-how-agents-understand-data-relationships) has more details on how agents can understand XLake data schema and relationships.

# **5\. XLake API**

The XLake Unified API is the interface through which all ActBI agents and the application interact with semantic knowledge, schemas, dashboards, business logic, and real or simulated data. It abstracts away the physical storage engines (OLAP, relational, vector store, object store).

The XLake exposes a unified API composed of **three high-level clients**, each with a strictly defined responsibility:

1. **Data Client** — datasets and raw data access  
2. **Visualization Client** — charts, dashboards, and visual state  
3. **Business Client** — business knowledge, semantics, schema meaning, and conversations

This separation ensures:

* clear separation of concerns  
* simpler agent reasoning  
* clean permission boundaries  
* long-term stability of the API as storage and engines evolve

All calls are scoped by `TenantContext` and `UserContext`.

## **5.1 Security & User Context Model**

All XLake API operations require a **UserContext**, which governs:

* **data visibility**  
* **dashboard visibility**  
* **schema visibility**  
* **RAG visibility**  
* **simulation visibility**  
* **lineage visibility**

### 5.1.1 UserContext Structure

UserContext {  
  "user\_id": "...",  
  "tenant\_id": "...",  
  "role": "viewer | analyst | manager | executive | admin",  
  "permissions": {  
      "can\_view\_fields": \[...\],  
      "can\_view\_tables": \[...\],  
      "can\_view\_kpis": \[...\],  
      "can\_view\_dashboards": \[...\],  
      "can\_run\_queries": true,  
      "can\_modify\_schema": false  
  },  
  "preferences": {  
    "units": "EUR",   
    "timezone": "Europe/Rome",  
    "verbosity": "concise"  
  }  
}

### 5.1.2 Security Guarantees

* Row/column access filtering is enforced at **query time**.  
* Semantic search results are **filtered by permissions**.  
* Dashboard/story access is restricted per user role.  
* Simulation datasets follow the same permission model as real data.

This ensures agents never hallucinate or leak restricted information.

## **5.2 Entity Model**

The XLake operates over a unified set of **entities**, each representing a meaningful unit in the customer or domain knowledge space. Entities are the nodes of the logical semantic graph.

### 5.2.1 Types of Entities

#### **Data Entities**

* **Table**  
* **Field / Column**  
* **KPI / Metric**  
* **Dataset** (materialized view, simulation dataset)  
* **External dataset signal** (weather, market, regulatory)

#### **Knowledge Entities**

* **Business concepts** (churn, margin, cost-of-goods)  
* **Document chunks** (paragraphs, sentences, tables)  
* **Extracted metadata** (Type B behavioral statements)

#### **Dashboard Entities**

* **Chart**  
* **ChartStack**  
* **Dashboard**  
* **Active filters**  
* **Active simulation overlays**

### 5.2.2 Entity Structure

Every entity has:

{  
  "entity\_id": "...",  
  "entity\_type": "field | table | kpi | concept | doc\_chunk | external\_signal | scenario | chart | dashboard",  
  "name": "...",  
  "metadata": {...},  
  "relationships": \[...\],  
  "embedding": \[ ... optional vector ... \],  
  "tenant\_id": "...",  
  "permissions": {...}  
}

### 5.2.3 Entity Principles

* Entities belong to a **tenant namespace**.  
* Entities may be enriched through user or agent-added metadata.  
* Entities are versioned when underlying data or definitions change.  
* Semantically similar entities are discoverable via RAG.  
* Agents operate on entities, never directly on storage layers.

## **5.3 Data Client**

### **Purpose**

The **Data Client** provides access to **datasets and raw data only**, independent of business meaning or interpretation.

It is responsible for:

* retrieving data from the DataLakeStore, connectors, simulations, and document-derived tables  
* registering new datasets produced by pipelines or agents  
* accessing raw documents from the object store

It does **not** provide:

* definitions  
* explanations  
* KPI logic  
* schema semantics  
* business facts

### **Responsibilities**

* Query structured datasets using explicit schemas and filters  
* Register datasets generated by pipelines or agents  
* Expose dataset metadata (shape, columns, freshness, lineage)  
* Fetch raw documents and binary assets  
* Surface data availability to other clients and agents

### **Illustrative API Surface**

Data.get\_dataset\_schema()

Data.query()

Data.list\_datasets()

Data.add\_dataset()

Data.get\_dataset\_metadata()

Data.get\_dataset\_lineage()

Data.fetch\_document()

Data.list\_documents()

### **Explicit Non-Responsibilities**

The Data Client **never**:

* explains what a field means  
* defines KPIs or metrics  
* infers joins or relationships  
* answers “why” questions  
* reasons about business concepts

Those concerns are handled exclusively by the **Business Client**.

## **5.4 Visualization Client**

### **Purpose**

The **Visualization Client** manages all **visual representations and UI state**, excluding the underlying data itself.

It handles *how data is presented*, not *what the data means* or *how it is computed*.

### **Responsibilities**

* Create and manage charts and dashboards  
* Maintain chart stacks, filters, layouts, and annotations  
* Store visualization rules and conventions  
* Support navigation, cloning, publishing, and versioning  
* Track dashboard-level narrative context (titles, highlights, annotations)

### **Illustrative API Surface**

Visualization.create\_chart()

Visualization.update\_chart()

Visualization.get\_chart()

Visualization.list\_charts()

Visualization.create\_dashboard()

Visualization.update\_dashboard()

Visualization.get\_dashboard()

Visualization.clone\_dashboard()

Visualization.publish\_dashboard()

Visualization.get\_visualization\_rules()

### **Notes**

* Chart **data** is always fetched via the **Data Client**  
* Chart **meaning** (e.g. what a metric represents) is resolved via the **Business Client**  
* The Visualization Client is UI- and state-oriented

## **5.5 Business Client**

### **Purpose**

The **Business Client** is the **semantic and knowledge layer** of XLake.

It owns everything related to:

* business meaning  
* domain knowledge  
* schema semantics  
* KPI definitions  
* relationships between entities  
* business facts and explanations  
* conversational and inferred knowledge

### **Responsibilities**

* Define and retrieve KPI and metric definitions  
* Manage schema semantics (entities, fields, joins)  
* Store and retrieve business explanations and rules  
* Maintain relationships between data entities  
* Perform semantic search and graph reconstruction  
* Store and retrieve conversation-derived knowledge and insights

### **Illustrative API Surface**

Business.get\_kpis()

Business.get\_kpi\_definition()

Business.add\_kpi\_definition()

Business.get\_schema\_semantics()

Business.add\_schema\_relationship()

Business.add\_business\_fact()

Business.semantic\_search()

Business.semantic\_graph()

Business.get\_conversation\_context()

Business.add\_conversation\_insight()

## **5.6 How the Clients Work Together**

A typical reasoning flow:

1. **Business Client**  
   * Resolve entities, terms, KPIs, and schema meaning  
2. **Data Client**  
   * Fetch or generate the required datasets using explicit schemas  
3. **Visualization Client**  
   * Create or update charts and dashboards  
4. **Business Client**  
   * Add explanations, insights, and narrative context

Each client does **one thing well**, and agents never confuse:

* data with meaning  
* meaning with presentation

It’s important to link the conversation and chart modifications together so we can track diffs between chart changes and what conversations triggered them. Like a story of how the dashboard was created or explored. In other words we should have the concept of:

* Conversation Message ←→ Visual change / Explanation to the User  
* The Conversation and Dashboard/Chart [Protobuf definitions](https://docs.google.com/document/d/1do7PPVFTVbUzOZ30i9cX1cbQIN3YUdabKJWJY4ziqKI/edit?tab=t.0#heading=h.kzhgpyimohj) can allow for these links to happen.

## **5.7 Why This Boundary Matters**

This design:

* keeps agent prompts shorter and clearer  
* prevents semantic leakage into data access  
* allows schema meaning to evolve independently of storage  
* makes it easier to swap OLAP engines or vector stores  
* mirrors how humans reason about data systems

Most importantly, it ensures that **all schema-entity knowledge lives in one place**: the **Business Client**.

# **6\. Data Ingestion, Refresh, & Embedding**

The XLake leverages the “[Data Platform Architecture](https://docs.google.com/document/d/1Hq9GODl4SPNAQh7i6-g7IOpmDyWtHbdQ/edit)” for the **semantic ingestion and indexing pipelines**. These pipelines ensure that every field, table, document, concept, KPI, and relationship is discoverable by agents through RAG (Retrieval-Augmented Generation).

XLake focuses on three fundamental actions:

1. **Ingest new information**  
2. **Refresh and re-index information when underlying data changes**  
3. **Update knowledge based on human input or agent-derived insights**

## **6.1 What We Index and Embed**

To support consistent semantic search and reasoning, the XLake embeds the following entities:

### 6.1.1 Fields (Columns)

For each field in the customer schema we embed:

* field name  
* cleaned/expanded name (“price\_per\_kg” → “price per kilogram”)  
* type (numeric, categorical, datetime)  
* units (kg, eur, %)  
* descriptive metadata (from documents or manual inputs)  
* statistical hints (distribution notes, uniqueness, typical ranges)  
* relationships: “used\_in\_KPI\_X”, “joins\_to\_Y.customer\_id”

### 6.1.2 Tables

For each table:

* table name  
* inferred entity/type (fact table, dimension table, event table)  
* description from source systems  
* fields \+ semantic summaries  
* join candidates  
* primary business purpose (e.g., “sales transactions”, “customer master”)

### 6.1.3 KPIs & Metrics

* KPI names  
* formulas  
* lineage (which fields and tables they depend on)  
* interpretations and business meaning  
* units and time granularity  
* domain mapping to core concepts

### 6.1.4 Document Chunks (From CustomerDocStore)

Chunked using rules in Section 6.2 below:

* paragraphs  
* tables  
* bullet lists  
* definitions  
* business rules (“price rises after storms”)

Each chunk is embedded separately to maximize recall.

### 6.1.5 Extracted Metadata (Type B Metadata)

Standalone sentences that describe:

* relationships (“lead time depends on supplier reliability”)  
* behaviors (“sales drop after holiday week”)  
* calculations (“margin \= revenue \- cost”)  
* constraints (“a batch is invalid if defect\_rate \> 3%”)

These are **first-class nodes** in the semantic graph.

### 6.1.6 External Signals (CoreExternalSourceStore)

* weather events  
* market trends  
* commodity prices  
* macroeconomic indicators

Embedded with semantic tags for cross-domain inference:  
 “storm intensity”, “inflation pressure”, “supply chain disruption”.

### 6.1.7 Domain Concepts (CoreContextStore)

* financial concepts (COGS, AR, churn, gross margin)  
* logistics concepts (lead time, throughput)  
* marketing concepts (CAC, LTV)

Mapped to customer-specific terms during ingestion.

## **6.2 Chunking Strategy (Documents & Schemas)**

Agents can only retrieve good context if the chunks themselves are high-quality.  
 We follow four chunking strategies:

### 6.2.1 Document Chunking Strategy

**Goal: maximize semantic recall without noise.**

We use a hybrid chunking method:

### **Rule A — Paragraph-Based Chunking**

Recommended for:

* narrative reports  
* strategy docs  
* audit notes

### **Rule B — Table Chunking**

Each table is extracted and embedded separately with:

* header row  
* cleaned column names  
* summary of the table (“Supplier performance by defect rate”)

### **Rule C — Sentence-Level Chunking for Metadata**

Metadata statements (Type B) are stored as **single-sentence embeddings** to maximize retrieval accuracy.

### **Rule D — Context Windows**

When embedding paragraph chunks, we store overlapping segments:

* 150–250 tokens  
* with 20% overlap

This balances precision and recall.

### 6.2.2 Schema Chunking Strategy

We chunk schema information into:

1. **Field-level chunks**  
   * name, type, meaning, stats, relationships

2. **Table-level chunks**  
   * domain role, join keys, summary description

3. **Join-level chunks**  
   * “sales.customer\_id → customers.customer\_id”

4. **KPI-level chunks**  
   * formula \+ lineage → embedded as one self-contained chunk

Each chunk has:

* a primary embedding vector  
* secondary metadata (JSON)  
* pointers to related entities

## **6.3 Indexing Strategy in Qdrant**

Qdrant supports:

* custom metadata fields  
* named collections  
* per-tenant segmentation  
* HNSW vector indexes  
* payload-based filtering

We create the following **collections per tenant**:

* `fields`  
* `tables`  
* `kpis`  
* `doc_chunks`  
* `metadata_sentences`  
* `relationships`  
* `external_signals`  
* `concepts`

Each vector has:

{  
  "vector": \[...\],   
  "payload": {  
    "tenant\_id": "...",  
    "entity\_type": "field | table | kpi | doc\_chunk | metadata | concept",  
    "entity\_id": "...",  
    "source": "document | schema | external | user\_input | agent",  
    "timestamp": "2025-02-10T10:00:00Z",  
    "confidence": 0.87,  
    "related\_entities": \["field:price\_per\_kg", "concept:weather"\],  
    "version": 3  
  }  
}

This allows agents to retrieve:

* “all metadata related to field X”  
* “all chunks describing margin”  
* “the most relevant external signals for this KPI”

## **6.4 Ingestion Use Case 1: New Information**

Triggered by:

* new document  
* new text input  
* new connector  
* new table or KPI

Pipeline actions:

1. detect new content  
2. extract structure (Type A) and metadata (Type B)  
3. generate embeddings  
4. infer relationships (joins, concepts, correlations)  
5. update XLake stores  
6. record lineage

All async, tenant-scoped.

## **6.5 Ingestion Use Case 2: Refresh Based on Data Changes**

Triggered by:

* schema drift  
* updated external datasets  
* changes in KPIs  
* document re-upload  
* data platform signals (Dagster/dbt)

Pipeline actions:

1. detect changes  
2. re-embed only the affected chunks  
3. update or delete semantic edges  
4. regenerate field/table stats  
5. refresh join recommendations  
6. recompute KPI graph if needed

We avoid full re-indexing — **only changed nodes** are reprocessed.

## **6.6 Ingestion Use Case 3: Human & Agent Knowledge Updates**

Knowledge does not always arrive through documents. It also comes from:

* manually added business rules  
* customer explanations  
* notes from analysts  
* insights generated during conversations  
* clarifications (“supplier reliability affects lead time”)  
* correction statements (“margin is NOT revenue \- cost, use formula X”)

These go through a **knowledge update pipeline**:

1. receive text or explanation  
2. classify into:  
   * correction  
   * explanation  
   * relationship  
   * KPI definition  
   * metadata sentence  
3. embed as Type B metadata  
4. attach to fields/concepts/tables/KPIs  
5. infer new relationships if applicable  
6. update semantic graph

Because this pipeline runs **independent** of structured data pipelines, the XLake can grow semantically even if no new data arrives.

## **6.7 Summary of XLake Knowledge Processing**

| Action | Trigger | Output | Stores Updated |
| ----- | ----- | ----- | ----- |
| **New ingestion** | doc upload, new schema | new chunks, data tables, metadata | DocStore, ContextStore, ChartStore |
| **Refresh** | schema drift, external updates | re-embedded chunks, updated edges | ContextStore, ExternalSourceStore |
| **Knowledge updates** | human input, agent-derived statements | new metadata, semantic links | ContextStore |
| **Embedding** | freq. scheduled or triggered | vector index entries | Qdrant |
| **Relationship inference** | embeddings, heuristics | semantic edges | ContextStore |
| **Lineage capture** | all ingestion | query lineage, document lineage | AppLogicStore |

# **7\. Simulated Data Management**

The XLake supports not only customer ground-truth data but also *simulated*, *forecasted*, and *scenario-driven* datasets generated by ActBI agents. These “parallel truth” datasets are essential for executive workflows such as forecasting, what-if analysis, and scenario comparison.

Simulated data is treated as a **first-class citizen** inside the XLake, but it remains **strictly separated** from the customer’s operational databases and ground-truth warehouse to avoid contamination, maintain trust, and preserve lineage.

This section describes how XLake stores, indexes, serves, and versions simulated data.

## **7.1 Where Simulated Data Lives**

Simulated datasets are stored as **parquet files** in the **Object Store**, under a dedicated namespace inside the CustomerDataLakeStore:

/customers/{tenant\_id}/scenarios/{scenario\_id}/  
    inputs/          (scenario config, parameters, assumptions)  
    outputs/  
        parquet/     (all simulated tables)  
        metadata.json

This ensures:

* strong tenant isolation  
* append-only versioning  
* fast analytical access  
* compatibility with OLAP engines

Simulated data mimics the shape of real fact/dimension tables, enabling seamless joins and comparisons.

## **7.2 Serving Simulated Data via the OLAP Engine**

All simulated datasets are served exclusively through the **OLAP engine** (e.g., ClickHouse/Tinybird/Trino/DuckDB, depending on deployment mode).  
 The OLAP engine reads parquet files directly from object storage, exposing each scenario as **virtual analytical tables**, for example:

sales\_fact\_\_real  
sales\_fact\_\_scenario\_42  
sales\_fact\_\_scenario\_42\_v2  
inventory\_fact\_\_scenario\_peakDemand

This allows agents and dashboards to:

* run SQL queries over simulation tables  
* JOIN real and simulated data  
* compute deltas (e.g., “margin difference between real and scenario 42”)  
* overlay charts from simulated and real data

No data is copied into the customer’s internal warehouse.

## **7.3 How Simulated Data Is Generated**

Simulated data is produced by a dedicated agent—the **Scenario Agent**—which uses the XLake to fetch relevant real data and then leverages the **ActBI Data Platform Pipelines** to perform the heavy lifting.

### **Generation Pipeline Flow**

1. **Agent receives prompt**  
    e.g., *“simulate a 7% price drop in NE region”*  
2. **Agent resolves baseline schema/data** via XLake  
   * identifies tables, fields, KPIs  
   * fetches baseline datasets through OLAP  
3. **Agent defines transformation logic**  
   * e.g., `price = price * 0.93`  
4. **Agent triggers a Data Platform pipeline job**  
    The Data Platform:  
   * loads baseline parquet (or fetches via connector)  
   * applies transformations  
   * validates schema consistency  
   * outputs the final simulation dataset as parquet  
5. **Pipeline writes output parquet** to the scenario namespace.  
6. **XLake registers the new scenario**:  
   * schema  
   * lineage  
   * metadata  
   * semantic tags  
   * embedding entries

This hybrid model guarantees:

* deterministic results  
* reproducibility  
* clean separation between semantic reasoning (XLake) and physical data processing (Data Platform)

## **7.4 Scenario Metadata & Lineage**

Each scenario has a metadata file describing:

{  
  "scenario\_id": "scenario\_2025\_42",  
  "description": "Price decreases by 7% in NE region",  
  "created\_at": "...",  
  "agent\_id": "scenario-agent",  
  "base\_tables": \["sales\_fact\_2024Q4"\],  
  "transformations": \["price \= price \* 0.93"\],  
  "parameters": {"discount": 0.07, "region": "NE"},  
  "hash\_of\_inputs": "...",  
  "version": 1  
}

This supports:

* lineage reconstruction  
* version comparison  
* reproducibility  
* debugging  
* RAG retrieval and explanation

The XLake stores references to these metadata files in the **CustomerAppLogicStore**, enabling UX components (scenario chips, overlays) to discover and display them.

## **7.5 RAG Integration and Semantic Indexing**

Simulated data and scenario descriptions are embedded and indexed in Qdrant. Indexed content includes:

* scenario descriptions  
* transformation rules

* KPIs impacted  
* scenario lineage  
* differences vs real values (summarized by the agent)  
* user notes and comments

This enables agents to answer questions like:

* *“Which scenario increases margin most in EMEA?”*  
* *“Compare scenario 42 with scenario 43.”*  
* *“Why does scenario 19 reduce revenue?”*

Embedding strategies:

* Scenario descriptions → sentence-level embeddings  
* Metadata.json → field-by-field embeddings  
* Summarized impacts → chunked embeddings  
* KPI deltas → per-KPI embeddings

All embeddings are stored in the **CustomerContextStore**.

## **7.6 Using Scenarios in Dashboards**

Dashboards treat simulation data as **scenario layers**:

* Real data \= baseline (solid line)  
* Scenario data \= overlay (dashed or tinted line)  
* Multiple scenarios \= small multiples or selectable chips

ActBI UI uses:

* Scenario filter chips  
* Chart overlays  
* Delta and KPI impact callouts  
* Version selection

The dashboard engine simply queries:

SELECT \* FROM sales\_fact\_\_scenario\_42 WHERE region \= 'NE'

or, for comparison:

SELECT   
    real.revenue,  
    sim.revenue as scenario\_revenue,  
    sim.revenue \- real.revenue as delta  
FROM sales\_fact\_\_real real  
JOIN sales\_fact\_\_scenario\_42 sim  
    USING (customer\_id, date)

## **7.7 Versioning and Lifecycle**

Each simulated dataset has a lifecycle:

1. **Draft** – produced but hidden from dashboards  
2. **Published** – visible to dashboards and RAG  
3. **Archived** – removed from active RAG, preserved for lineage  
4. **Deleted** – physically removed after retention period

Versioning:

scenario\_42\_v1  
scenario\_42\_v2  
scenario\_42\_v3

Reasons for new versions:

* different parameters  
* corrected logic  
* user-provided explanations  
* model improvements  
* changes in baseline data

Versioning ensures reproducibility and explainability.

## **7.8 Why Simulated Data Lives Outside Customer Databases**

This architectural choice:

* prevents accidental contamination of operational data  
* avoids conflicts with customer DB permissions

* enables unrestricted exploration  
* makes cleanup trivial  
* supports unlimited scenario versions  
* keeps scenarios governed by ActBI, not the customer DBAs  
* ensures agents and dashboards can toggle scenarios without friction

Executives always know what is *real* vs *simulated*.

# **References:**

* [https://github.com/pthom/northwind\_psql/blob/master/northwind.sql](https://github.com/pthom/northwind_psql/blob/master/northwind.sql) (for test data to “connect” to) \[[Our Copy in Supabase](https://supabase.com/dashboard/project/gwvskyiechyfkqoksqjq/database/schemas)\]

# **APPENDIX 1: PROTOCOL BUFFER SCHEMA AND DIFF RULES** {#appendix-1:-protocol-buffer-schema-and-diff-rules}

This appendix defines the **canonical object model for ActBI**, the **serialization rules** used to generate stable JSON for LLM reasoning, and the **diff pipeline** used by both agents and engineers to compare versions of dashboards, charts, and insights.

## **1\. ActBI Protobuf Schema v1**

The schema is designed to be:

* **LLM-friendly**

* **stable over time**

* **safe to evolve**

* **structured enough to prevent drift**

* **consistent across Python \+ TypeScript**

Our directory structure:

actbi/v1/  
    chart.proto  
    chart\_stack.proto  
    dashboard.proto  
    dashboard\_layout.proto  
    conversation.proto

Below are the full contents.

---

# **📄 actbi/v1/chart.proto**

syntax \= "proto3";

package actbi.v1;

// Generic scalar value that can hold any chart-specific datapoint attribute.  
message Value {  
  oneof kind {  
    double number \= 1;  
    string text \= 2;  
    bool flag \= 3;  
  }  
}

// A versatile, future-proof datapoint that supports all ECharts styles.  
message DataPoint {  
  // 1\. UNIVERSAL FIELDS (used by 90% of charts)  
  double x \= 1;         // optional (line, bar, scatter, heatmap x-axis)  
  double y \= 2;         // optional (line, bar, scatter, heatmap y-axis)  
  string category \= 3;  // optional (pie, funnels, categorical axes)  
  double value \= 4;     // optional (pie slice value, heatmap intensity)

  // 2\. MULTI-DIMENSIONAL COORDINATES  
  double z \= 5;         // optional (3D charts)  
  double lat \= 6;       // optional (geo charts)  
  double lon \= 7;       // optional (geo charts)

  // 3\. FINANCIAL (CANDLESTICK/K-LINE)  
  double open \= 8;  
  double close \= 9;  
  double low \= 10;  
  double high \= 11;  
  double volume \= 12;

  // 4\. NETWORK/SANKEY/TREEMAP  
  string source \= 13;  
  string target \= 14;

  // 5\. RADAR CHART  
  repeated double radar\_values \= 15;

  // 6\. EXTENSIBLE ATTRIBUTES (customizable for any chart type)  
  map\<string, Value\> attributes \= 16;

  // 7\. OPTIONAL LABEL  
  string label \= 17;  
}

message DataSeries {  
  string id \= 1;  
  string name \= 2;  
  repeated DataPoint data \= 3;  
}

message Filter {  
  string field \= 1;  
  string operator \= 2;  
  string value \= 3;  
}

message Dimension {  
  string field \= 1;  
  string type \= 2;   // "time", "category", "numeric"  
}

message Insight {  
  string id \= 1;  
  string summary \= 2;  
  string detail \= 3;  
  double confidence \= 4;  
}

message Chart {  
  string id \= 1;  
  string title \= 2;  
  string chart\_type \= 3;   // "bar", "line", "area", etc.

  repeated Dimension dimensions \= 4;  
  repeated Filter filters \= 5;  
  repeated DataSeries series \= 6;

  Insight insight \= 7;

  google.protobuf.Timestamp created\_at \= 8;  
  google.protobuf.Timestamp updated\_at \= 9;

  uint32 version \= 10;        // increments on mutation  
  uint32 schema\_version \= 11; // schema-level version  
}  
---

### Note on how we can use the versatile DataPoint (Examples):

#### Line chart

x=1, y=100

#### Pie chart

category="Marketing", value=42

#### Candlestick

open=100, close=120, low=95, high=130

#### Geo scatter

lat=40.73, lon=-73.93, value=200

#### Radar

radar\_values=\[80, 55, 72, 91\]

#### Heatmap

x=2, y=3, value=92

#### Custom attribute

attributes\["symbolSize"\] \= number: 16  
---

# **📄 actbi/v1/chart\_stack.proto**

syntax \= "proto3";

package actbi.v1;

import "chart.proto";  
import "google/protobuf/timestamp.proto";

message ChartStack {  
  string id \= 1;  
  string title \= 2;

  repeated Chart charts \= 3;

  google.protobuf.Timestamp created\_at \= 4;  
  google.protobuf.Timestamp updated\_at \= 5;

  uint32 schema\_version \= 6;  
}

---

# **📄 actbi/v1/dashboard\_layout.proto**

syntax \= "proto3";

package actbi.v1;

// Placement of a single chart inside a dashboard.  
message ChartPlacement {  
  string chart\_id \= 1;  
  uint32 level \= 2;   // 1, 2, 3, 4 based on UX Architecture  
  uint32 order \= 3;   // optional ordering within each level  
}

// Full layout specification for a dashboard.  
message DashboardLayout {  
  repeated ChartPlacement placements \= 1;  
}

---

# **📄 actbi/v1/dashboard.proto**

syntax \= "proto3";

package actbi.v1;

import "chart\_stack.proto";  
import "dashboard\_layout.proto";  
import "google/protobuf/timestamp.proto";

message Dashboard {  
  string id \= 1;  
  string title \= 2;  
  string description \= 3;

  // Content lineage  
  repeated ChartStack stacks \= 4;

  // Presentation and UX layering  
  DashboardLayout layout \= 5;

  google.protobuf.Timestamp created\_at \= 6;  
  google.protobuf.Timestamp updated\_at \= 7;

  uint32 schema\_version \= 8;  
}

---

# **📄 actbi/v1/conversation.proto**

(**MessageContext lives here per your request**)

syntax \= "proto3";

package actbi.v1;

import "google/protobuf/timestamp.proto";

// Conversation-related metadata that guided the LLM.  
message MessageContext {  
  string mode \= 1;            // "reporter", "interpreter", "explorer", “admin”  
  string task \= 2;            // "consult", "reflect", etc.  
  string narrative\_hint \= 3;  // optional: "explain variance in KPIs"  
  string model \= 4;           // "gpt-5", "claude-3", etc.  
}

// A single conversational message that may lead to chart mutations.  
// The relationship between this message and chart versions is stored in the DB.  
message Message {  
  string id \= 1;

  string sender \= 2;         // "user" or "assistant"  
  string text \= 3;           // natural lang content  
  MessageContext context \= 4;

  google.protobuf.Timestamp created\_at \= 5;  
}

// Full ordered conversation history.  
message Conversation {  
  string id \= 1;

  repeated Message messages \= 2;

  // Optional associations for convenience.  
  repeated string dashboard\_ids \= 3;  
  repeated string chart\_stack\_ids \= 4;

  google.protobuf.Timestamp created\_at \= 5;  
  google.protobuf.Timestamp updated\_at \= 6;  
}

### **Clean layering & separation**

* Charts \= pure data  
* ChartStacks \= pure grouping  
* Dashboards \= stacks \+ layout  
* Layout \= separate, flexible structure  
* Conversation \= reasoning \+ messages only  
* DB \= relationships & versioning

### **Maximum LLM-friendliness**

Each message can be paired with:

* chart before  
* chart after  
* diff  
* message.context

All without polluting the schema.

### **Maximum evolution flexibility**

Future changes can safely extend:

* layout (grid, responsive sizes)  
* message types  
* multi-agent workflows  
* dashboard-level metadata

Charts remain forward/backward compatible thanks to protobuf discipline.

### **Supports auditability & lineage**

You can reconstruct:

chart\_v1 → chart\_v2 → chart\_v3

from the conversation log \+ the chart-version table.

## **2\. Canonical JSON Serialization Rules**

These rules ensure **deterministic, LLM-friendly JSON snapshots** generated from protobuf objects.

### Rule 1 — JSON sorting (alphabetical keys)

All JSON must be serialized with keys sorted lexicographically.

Python:

json.dumps(obj, indent=2, sort\_keys=True)

Node:

JSON.stringify(obj, null, 2, { sortKeys: true })

(This ensures diffs are stable even as fields are added.)

### Rule 2 — No omitted fields (explicit nulls only for optionals)

Protobuf's `MessageToDict` omits empty/zero-value fields by default.  
 **ActBI overrides this**:

* All optional fields: **emit null**  
* All repeated fields: **emit \[\]**  
* All nested messages: **emit {} when empty**

Python:

MessageToDict(  
    proto\_obj,  
    including\_default\_value\_fields=True,  
    preserving\_proto\_field\_name=True  
)

This prevents:

* accidental deletions  
* missing fields in diffs  
* unstable snapshots

### Rule 3 — Preserve protobuf field names (snake\_case)

UI may adapt to camelCase, but canonical JSON uses **proto field names**.

This avoids:

* engineer-renames  
* UI-invented keys  
* drift between clients

### Rule 4 — Timestamp format

Use ISO8601:

"2025-11-28T14:33:51Z"

Never emit epoch numbers — epoch values cause unnecessary diffs.

### Rule 5 — Schema version always included

Every object includes:

"schema\_version": 1

LLMs can compare `schema_version` changes as part of their diff reasoning.

### Rule 6 — Deterministic ordering of arrays

For reproducibility:

* Sort `series` by `id`  
* Sort `filters` by `field`  
* Sort `dimensions` by `field`  
* Sort `charts` inside stacks by `id`

This ensures LLM diffs do not reorder lists unless explicitly changed.

## **3\. ActBI Diff Pipeline (Python \+ Node)**

This pipeline produces stable, line-by-line diffs suitable for:

* LLM tool calls  
* agentic corrections  
* dashboard evolution snapshots  
* semantic drift detection

### Pipeline Overview

Protobuf Object (old)  
    ↓ serialize  
Canonical JSON (old.json)  
    ↓  
Protobuf Object (new)  
    ↓ serialize  
Canonical JSON (new.json)  
    ↓  
Unified Diff (LLM-friendly)

All diffs are **textual**.  
 LLMs handle textual diffs extremely well.

### Python Diff Implementation

from google.protobuf.json\_format import MessageToDict  
import json, difflib

def to\_canonical\_json(proto\_obj):  
    obj \= MessageToDict(  
        proto\_obj,  
        including\_default\_value\_fields=True,  
        preserving\_proto\_field\_name=True  
    )  
    return json.dumps(obj, indent=2, sort\_keys=True)

def diff\_protos(old\_proto, new\_proto):  
    old\_json \= to\_canonical\_json(old\_proto).splitlines()  
    new\_json \= to\_canonical\_json(new\_proto).splitlines()

    diff \= difflib.unified\_diff(  
        old\_json,  
        new\_json,  
        fromfile="old.json",  
        tofile="new.json",  
        lineterm=""  
    )  
    return "\\n".join(diff)

Usage:

print(diff\_protos(old\_dashboard, new\_dashboard))

Produces:

\--- old.json  
\+++ new.json  
@@  
\- "title": "Revenue Q4"  
\+ "title": "Revenue Q4 (Updated)"

@@ stacks\[0\].charts\[1\].filters\[0\]  
\- "value": "EMEA"  
\+ "value": "North America"

### Node.js (Next.js) Diff Implementation

Use `protobufjs` \+ `json-stable-stringify` \+ `diff`.

import { diffLines } from "diff";  
import stableStringify from "json-stable-stringify";

function toCanonicalJSON(obj: any): string {  
  return stableStringify(obj, { space: 2 });  
}

export function diffJSON(oldObj: any, newObj: any): string {  
  const oldJson \= toCanonicalJSON(oldObj);  
  const newJson \= toCanonicalJSON(newObj);

  return diffLines(oldJson, newJson)  
    .map(part \=\>  
      (part.added ? "+" : part.removed ? "-" : " ") \+ part.value  
    )  
    .join("");  
}

## **4\. Schema Evolution Rules (v1 → v2 → v3)**

ActBI uses protobuf’s evolution guarantees:

### Allowed without breaking:

✔ Add new optional fields  
 ✔ Add new repeated fields  
 ✔ Add new nested messages  
 ✔ Deprecate fields without removing  
 ✔ Rename field **names** (not numbers)  
 ✔ Change defaults  
 ✔ Add enums

### Forbidden:

❌ Reusing a field number  
 ❌ Changing field types  
 ❌ Removing fields entirely  
 ❌ Changing repeated → non-repeated  
 ❌ Moving fields into `oneof`

These rules guarantee:

* **diff stability**  
* **predictable LLM behavior**  
* **safe migration of stored dashboards**  
* **structural integrity across versions**

## **5\. Recommended Evolution Strategy for ActBI**

When you add a field to a Chart:

string subtitle \= 12;

Steps:

1. Bump `schema_version` to `2`  
2. Add field with **new field number**  
3. Default to `null` (or empty string)  
4. Canonical JSON serializer will emit:

"subtitle": null

LLM diff examples stay clean:

\+ "subtitle": "Quarterly Revenue Overview"

## **6\. Sample Canonical JSON Output (v1)**

{  
  "chart\_type": "bar",  
  "context": {  
    "mode": "interpreter",  
    "narrative\_hint": null,  
    "task": "consult"  
  },  
  "created\_at": "2025-11-28T13:45:11Z",  
  "dimensions": \[\],  
  "filters": \[\],  
  "id": "chart\_001",  
  "insight": {  
    "confidence": 0.91,  
    "detail": null,  
    "id": "ins\_001",  
    "summary": "Revenue increased 7% vs last month."  
  },  
  "schema\_version": 1,  
  "series": \[  
    {  
      "data": \[  
        { "x": 1, "y": 100, "label": null },  
        { "x": 2, "y": 107, "label": null }  
      \],  
      "id": "s1",  
      "name": "Revenue"  
    }  
  \],  
  "title": "Monthly Revenue",  
  "updated\_at": "2025-11-28T13:45:11Z"  
}

This structure is:

* highly diffable  
* stable  
* clean for LLM agents  
* strongly typed  
* resistant to engineering drift

# **APPENDIX 2: HOW AGENTS UNDERSTAND DATA RELATIONSHIPS** {#appendix-2:-how-agents-understand-data-relationships}

To help agents understand tables, fields, schemas, dependencies, and the logical graph of the XLake **without bloating prompts**, ActBI uses a small, stable instruction set combined with structured context objects retrieved at runtime.  
 Agents never receive full schema dumps inside the prompt. Instead, they receive **summary objects** describing:

* nodes (tables, columns, parquet files, metrics, external datasets),  
* edges (joins, lineage links, semantic relationships, business meaning),  
* roles (source, derived, KPI, dimension, fact, metadata),  
* constraints (filters, partition keys, time-grain), and  
* quality (confidence, validation status).

### **Principle: Small Prompt, Big Context**

The prompt stays short.  
 The *context object* (JSON) carries the complexity.

We follow three rules:

## **Rule 1 — All Relationships Are Logical, Not Physical**

Agents do NOT reason about internal infra (Postgres partitions, OLAP shard layout, Qdrant shards, etc.).  
 They reason only about the **XLake Logical Graph**:

* how entities relate,  
* how data aligns,  
* how to navigate links,  
* how to combine signals.

Thus, edges are semantic relationships such as:

* “customer\_id → order.customer\_id” (join)  
* “price\_per\_kg → impacted\_by → storm events” (metadata-derived link)  
* “sales table → derived metric → margin\_pct” (KPI lineage)  
* “doc metadata → enriches → product.quality\_score” (contextual link)

This lets us keep a clean, domain-centric graph the agents consistently use.

## **Rule 2 — Give the Agent a Minimal Instruction Contract**

We define a **short, universal instruction block** included in every agent:

### **Agent Instruction Contract (Minimal Prompt Block)**

**You operate over an XLake Logical Graph.**  
 You are given a JSON context object containing:

* entities (tables, metrics, files, fields)  
* logical relationships (edges)  
* business definitions  
* constraints  
* relevant slices of customer data

Your tasks:

1. **Interpret the user's question** in terms of graph entities and edges.  
2. **Resolve meaning** by using semantic links, not physical storage paths.  
3. **Select correct relationships** when joins/links exist.  
4. **Explain why you choose these links** when ambiguity exists.  
5. **Use metadata edges** (business meaning, document-derived notes, definitions, KPIs) to enrich reasoning.  
6. **Avoid hallucinations**—never invent fields or tables not present in the graph.  
7. **Ask for clarification** when the graph does not support the user’s meaning.

This contract is \< 100 words and never changes.

Everything else (schema, metadata, inferred relationships, KPIs, join logic) is passed through **dynamic context objects**, not prompt text.

## **Rule 3 — Provide a Small, Structured Relationship Object**

To avoid overwhelming the prompt window, the agent receives compact JSON objects representing only the entities relevant to the current question.

### **Example XLake Context Object (Greatly Simplified)**

{  
  "entities": {  
    "sales": {  
      "columns": \["order\_id", "customer\_id", "price\_per\_kg", "quantity", "date"\],  
      "roles": \["fact"\],  
      "description": "Sales transactions"  
    },  
    "customers": {  
      "columns": \["customer\_id", "region", "segment"\],  
      "roles": \["dimension"\],  
      "description": "Customer master table"  
    },  
    "weather": {  
      "columns": \["date", "region", "storm\_intensity"\],  
      "roles": \["external"\],  
      "description": "External weather dataset"  
    }  
  },  
  "edges": \[  
    {  
      "type": "join",  
      "from": "sales.customer\_id",  
      "to": "customers.customer\_id",  
      "confidence": 0.98  
    },  
    {  
      "type": "contextual",  
      "from": "sales.price\_per\_kg",  
      "to": "weather.storm\_intensity",  
      "relationship": "storms impact price fluctuations",  
      "source": "document\_metadata",  
      "confidence": 0.75  
    }  
  \],  
  "metrics": {  
    "margin\_pct": {  
      "formula": "(revenue \- cost) / revenue",  
      "lineage": \["sales"\],  
      "role": "kpi"  
    }  
  }  
}

This gives the agent:

* what connects to what  
* why  
* how confidently  
* and with which semantic meaning

without flooding the prompt.

## **How This Enables Agent Behavior**

### **1\. Natural Join Resolution**

The agent determines joins via edges:

“Link sales to customers using customer\_id (0.98 confidence).”

Not by guessing.

### **2\. Business Meaning Integration**

When user asks:

“How do storms affect price?”

The agent sees the contextual edge:

price\_per\_kg ←→ storm\_intensity  
 relationship \= “storms impact price fluctuations”

And automatically knows which tables to combine—even if storm data lives in a different source.

### **3\. Understanding Document-Derived Metadata**

If metadata says:

“The price per kg changes every time there is a storm.”

This becomes a contextual edge.  
 Agents treat it like domain knowledge—not prose.

### **4\. Avoiding Hallucinated Fields**

When the agent doesn’t see a node or edge, it refuses to invent one:

“`profit_margin` does not exist; available metrics are margin\_pct.”

### **5\. Explanation**

Agents can explain reasoning because they know:

* which edges were used  
* why  
* with what confidence

# **Notes:**

We will have 2 sets of storage engines: one for each customer (C) and one for actbi (P). 

We will use 4 types of storage technologies. We will need to figure out what is the best way to make each of these stores have full isolation between the ActBI-only data and the per-Customer data as well as provide isolation between Customers with the minimal amount of infrastructure duplication. But we need to take into account that each customer might request that the Customer-specific knowledge is deployed into a cloud provider of their own choice. We want to have a per-Customer C XLake that is part of our “ActBI Server” and the ActBI P XLake. The ActBI-only XLake will live in GCP. Ideally we want to have sharding/partitioning/isolation of the Customer XLake from a single instance deployed in each cloud provider and not have one XLake per customer.

1) RAG: We can leverage Qdrant that is deployed in Qdrant cloud at the cloud provider the customer wants.  
2) Relational DB: Postgres. We can use Supabase.  
3) OLAP DB: we can use Clickhouse managed: [https://www.tinybird.co/](https://www.tinybird.co/)   
4) Filesystem: for storing files. We can use the supabase object store or the AWS, GCP, Azure equivalents (e.g., S3 etc.)  
5) Cache: Redis. 

For each customer C we will have the following:

1\) a “CustomerContextStore” that keeps all the metadata for all other sources, especially parsed schema from the customer’s connected data sources and document drives. This uses the RAG for the indexed information and ObjectStore

2\) a "CustomerBusinessLogicStore" that keeps all the company's data that we have that powers the app: users, charts including generated filters, what-if scenarios, configurations, highlights etc., dashboards with the same associated agent-generated data that we need to load in the UI, conversations,  lineage, connector configs, settings, admin stuff etc. This uses the Relational DB and it lives in a single DB partitioned by tenant ID (a tenant can be a company or an individual who bought ActBI).

3\) a "CustomerDocStore" that keeps their documents. The contents of those documents will be split into two data sets (indexed in the RAG): actual data and metadata that describes the data. It is possible that the raw documents live in a shared drive actbi can connect to. If no such drive exists then we use our own file blob store (S3 or equivalent). The data items we extract from those docs will form a schema (which we will need to figure out how to generate/extract agentically or manually) and then we store that schema in our RAG for agentic access and the extracted data in parquet files we can serve via our OLAP DB. So the DocStore uses all 3 storage technologies: RAG, OLAP, Filesystem.

4\) A “CustomerChartStore” Chart Cache store where we put data that each dashboard needs to load to display in the UI (that is computed data that powers the charts). This uses the Cache for loading data points, the OLAP DB for pulling any computed KPIs that are missing from the Cache, and the Relational DB for pulling the dashboard descriptor data. This store needs to support the concept of materialized views or data sets. We could start without the Cache in the middle and add it later on if we have performance issues with the OLAP DB.

For ActBI P we will have the following:

1\) “CoreContextStore”. This is where we keep all our business domain knowledge (finance, customer, marketing, supply chain dictionaries and know how etc.) so we can understand relationships in our customer’s data fields and tables as well as the encoded expertise for how we build charts etc. 

2\) “CoreExternalDataStore”. This is where we keep any processed data we pick from 3rd party sources: weather, public financials, FDA reports etc. that we process using our pipelines and then save in parquet format. This uses the OLAP DB and the RAG.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIQAAAA1CAYAAACA0kN3AAAFBUlEQVR4Xu2asYvlZBTFkwdiYS2iuLA2YqmFoIW1rY2CCHYWFnYirJWKnY3OmDwHG+200f/AQkvH5I2zuOgWslpYyXYuirvP5PmSfPPLzU3uSzYEvT84qO+ec+ew94PdnTGKHMdxHMdxHMdxHGdeHv3qj+0SxZ7OTPAQSxF7OjPBQyxF7OnMBA+xFLGnMxM8xFLEns5M8BBLEXs6M8FDLEXs6cwED7EUsaczEzzEUsSezkzwEEsRe5bEafZLnObbUtF2G3PuTAAPsRSxZ/UQQkVJ/jh9zv+BNH+ej6F+FM7ErPPLgzWSt67dujxUYW6V5p/yIfiDuEvwF1gTs1bevnZrO1TMsstUnRzAX2BNzFrh0TUxG603L0zdxxHgL7ImZq3w6JqYdWaCR9fErBUeXROzzkzw6JqYtcKja2LWmQkeXROzVnh0Tcyyi9SJs9qTZC/XppPTBzmvtFrn7wfrBlHkbnAPVfz55wnmQuivcz3QPzSnwmWamLXCo2till2kTpzVnupBrDfPcibodrizk+T8kpBVxRUV9NX+o+v30ltRzH+gf6+r9JoQFnaKWSs8uiZm2UXqxFntKR/E8dkj/FxTuJfE6eY3+oeKuyrom9o/GC7UxKwVHl0Ts+wideKs9hQPgp8NUbi7YpXmn9BnFXeW0FN7j84eFry36dt5k/xJes1wqSZmrfDomphlF6kTZ2MV7q6gJ9Qq2XwQpd89FaX5Fc6gG9xbIvh2OtR3EFyqiVkrPLomZtlF6sSZoJ9Cf/Tx+QOCp1GSfxHa43X2fcvzr+/b0FdRzP5uefeit2SVZp/Rt/OmZ89UHs60fQfBxZqYtcKja2KWXaROnF3wrbNXQ28IvV37i7+FvFt89rPmIfT2ZegL/ask/5yf73WHew5GWN4pZq3w6JqYZRepE2ddPkLv0NwQuK9373H2EL07f5K/ws96dx0Cl2ti1gqProlZdpE6cdbla5FkL9I/KNcDdw3dS6+m4g+5HzI/Cn4BTcxa4dE1McsuUifOAn0T+lqcnD4mZFr7RT7Kni58vzPXJ64h9HeJudHwC2hi1gqProlZdpE6cdYo+zr0tbA+iOKvd/RZxZWk8PzFDBW9d3Yfc6PhF9HErBUeXROz7CJ14qzRdA+C80PFvS2EH/dTjEwCv4gmZq3w6JqYZRepE2eNpnkQxX/f4bxLUZo/t8+0Zrt5D/R3ibnR8AtoYtYKj66JWXaROnHWaLIH0ZrvdfH7GwGCt7WXFPM/6e+S9vOOg+AX0MSsFR5dE7PsInXirNEEDyLJ3+BsN0/zN4NNLehv7RWgt0/Mj4LLNTFrhUfXxCy7SJ04azT+QRT//iNn4bwL+vty9IV+flbPkvNL3HMwXK6JWSs8uiZm2UXqxFmjSR7ETc7CuURs/NZ1CX3083POR8PFmpi1wqNrYpZdpE6cNRr/IFZJdszZXjfDVRXKt5kv7A2hR/R2/NYVj/3/ICqExZ1i1gqProlZdpE6cdZo/IMo4Qz6Mkqz14p/XhdmLYV7S/Y/J2n54nX+K70tT8fOg+BSTcxa4dE1McsuUifOGs3yIEwK92q76dtxcnoPfarfAhdqYtYKj66JWXaROnHWaJoHUcK5Js0/ZGfx28ProS+E3jpzlN1Prwku1MSsFR5dE7PsInXirNF0D6KEHkl93iH7Qo8E/UNzzt1inb8UB9+9XCWbd2hxHMdxHMdxnP80/wACymyvt9zDuwAAAABJRU5ErkJggg==>