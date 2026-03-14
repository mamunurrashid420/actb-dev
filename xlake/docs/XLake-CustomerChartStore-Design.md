# **XLAKE CUSTOMER CHART STORE DESIGN**

# **1\. Purpose & Scope**

The **CustomerChartStore** manages all **chart-related artifacts** required to render dashboards in ActBI.

It is responsible for:

* Storing **versioned chart, chart stack, and dashboard specifications**  
* Storing **data bindings**, **ETL definitions**, and **output schemas**  
* Storing metadata for **materialized chart data**  
* Serving **render-ready chart data** to the UI  
* Enabling **lineage, auditability, and diffability**

It does **not**:

* Query OLAP engines directly  
* Perform analytical computation  
* Interpret natural language  
* Decide UI layout or rendering behavior

# **2\. High-Level Architecture Overview**

## **2.1 Two-Plane Architecture**

The CustomerChartStore is split into two explicit planes:

#### **Spec Plane (Control Plane)**

* Protobuf-based  
* Small, diffable, versioned  
* Captures **intent and structure**

#### **Data Plane (Serving Plane)**

* JSON-based  
* Immutable per version  
* Captures **materialized facts**

These planes evolve independently.

## **2.2 Core Artifacts**

**Spec Plane**

* Chart  
* ChartStack  
* Dashboard  
* DataBinding (the view of the data lake that contains the data we need)  
* OutputSchema (the shape of the data structure we feed to the visuals)  
* ChartDataSlice (metadata linking the source input to data processing to output)

**Data Plane**

* JSON data slices (actual rows)

## **2.3 Read, Write, and Refresh Paths**

#### **Write Path (Authoring / Mutation)**

Triggered by conversational reasoning:

1. ChartSpec / ChartStack / Dashboard is created or updated  
2. DataBinding is created or updated  
3. ETL definition (ibis \+ polars) is generated  
4. OutputSchema is derived  
5. ChartDataSlice metadata is registered

No data is fetched at this stage unless explicitly requested.

#### **Data Refresh Path (Deterministic, Non-Agentic)**

Triggered when data is needed:

1. UI requests a dashboard / chart stack / chart  
2. Store resolves required ChartDataSlices  
3. For each slice:  
   * Check cache / freshness policy (timestamp, TTL, hash)  
   * If fresh → serve existing JSON  
   * If stale or missing → execute ETL  
4. Materialized JSON is stored  
5. ChartDataSlice metadata is updated

**Important**:

* Data refresh is **not agent-driven**  
* Data refresh is **consistent across a full dashboard or chart stack**  
* All charts in a dashboard see the same refresh boundary

#### **Read Path (UI)**

1. UI requests dashboard / chart stack / chart  
2. Store returns:  
   * Spec artifacts (protobuf → JSON)  
   * ChartDataSlice references  
3. UI fetches JSON data slices  
4. Charts are rendered

# **3\. Core Design Principles**

* **Specs describe intent**  
* **DSL describes transformation**  
* **JSON describes facts**

Additional rules:

* Specs are immutable and versioned  
* Data is immutable per slice  
* Schema changes are explicit  
* Data refresh does not imply spec mutation  
* Declarative intent over imperative logic  
* No semantic leakage across layers

# **4\. Artifact Model**

This section defines **all artifacts**, their storage form, and examples.

## **4.1 Chart (Protobuf – Spec Plane)**

**Responsibility**  
Defines *how data should be interpreted and rendered*, not the data itself.

---

syntax \= "proto3";

package actbi.v1;

message Filter {  
  string field \= 1;  
  string operator \= 2;  
  string value \= 3;  
}

message Dimension {  
  string field \= 1;  
  string type \= 2;   // "time", "category", "numeric"  
}

message Chart {  
  string id \= 1;  
  string title \= 2;  
  string chart\_type \= 3;

  repeated Dimension dimensions \= 4;  
  repeated Filter filters \= 5;

  // References to materialized data  
  repeated string chart\_data\_slice\_ids \= 6;

  uint32 version \= 7;  
  uint32 schema\_version \= 8;  
}  
---

## **4.2 ChartStack (Protobuf – Spec Plane)**

**Responsibility**  
Narrative grouping of charts. We keep insights and recommendations decoupled.

---

syntax \= "proto3";

package actbi.v1;

import "chart.proto";  
import "google/protobuf/timestamp.proto";

message ChartStack {  
  string id \= 1;  
  string title \= 2;

  // Charts grouped in this stack  
  repeated Chart charts \= 3;

  // Metadata only (no insights / recommendations here)  
  google.protobuf.Timestamp created\_at \= 4;  
  google.protobuf.Timestamp updated\_at \= 5;

  uint32 schema\_version \= 6;  
}  
---

## **4.3 Dashboard (Protobuf – Spec Plane)**

**Responsibility**  
Composition \+ layout only.

---

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

syntax \= "proto3";

package actbi.v1;

import "chart\_stack.proto";  
import "dashboard\_layout.proto";  
import "google/protobuf/timestamp.proto";

message Dashboard {  
  string id \= 1;  
  string title \= 2;  
  string description \= 3;

  // Structural composition  
  repeated ChartStack stacks \= 4;

  // Presentation only  
  DashboardLayout layout \= 5;

  // Metadata  
  google.protobuf.Timestamp created\_at \= 6;  
  google.protobuf.Timestamp updated\_at \= 7;

  uint32 schema\_version \= 8;  
}

---

## **4.4 Insights & Recommendations (Protobuf – Spec Plane)**

* **Insights and Recommendations are not embedded** in Chart / ChartStack / Dashboard  
* They are **first-class artifacts** that *reference* what they annotate  
* Insights are classified by the type of observation (positive, negative, etc.) to help make them visually integrated for the user.  
* Insights use **Highlights**  
* Highlights are flexible on how they can be linked to data on a chart.  
* Recommendations are **calls-to-action** and do **not** use highlights.  
* Both support **scope**: chart, chart-stack, or dashboard (via **AnnotationTargets**)  
* Both are designed to **evolve over time independently** of visual specs.

### 4.4.1 Design Goals

Insights and recommendations must:

* Reference **specific evidence** in the data  
* Be visually explainable in charts  
* Survive data refreshes  
* Avoid duplicating data  
* Remain diffable and auditable

### 4.4.2 Evidence Referencing Model

Insights and recommendations reference **Highlights**, not raw data.

A Highlight is a **visual instruction**, not a data payload.

What a Highlight can reference

* A single row (e.g. outlier)  
* A set of datapoints (e.g. all values for a category)  
* A threshold or benchmark line  
* A value range

All references are made via:

* `chart_data_slice_id`  
* selectors (row IDs, field filters, numeric values)

No data is embedded.

| Highlight Type | Meaning |
| ----- | ----- |
| `row` | Emphasize specific data rows |
| `point_set` | Emphasize a subset of datapoints |
| `threshold` | Draw a reference line |
| `range` | Highlight a band or interval |

This abstraction allows the UI to:

* render highlights consistently  
* adapt to different chart types  
* evolve visualization styles without changing specs

This gives us:

* dashboard-level alerts (“Overall margin dropped 6%”)  
* stack-level insights (“Cost volatility concentrated here”)  
* chart-level observations (“Outliers detected in March”)

…without touching the ChartStack or Dashboard versions.

Insight and Recommendations are: 

* Stored in their own tables / collections  
* Queried by:  
  * dashboard\_id  
  * chart\_stack\_id  
  * chart\_id  
* Rendered alongside visuals, not inside them

---

message AnnotationTarget {  
  // Exactly one of these should be set  
  oneof target {  
    string chart\_id \= 1;  
    string chart\_stack\_id \= 2;  
    string dashboard\_id \= 3;  
  }  
}

---

message Highlight {  
  string id \= 1;

  // "row", "point\_set", "threshold", "range"  
  string type \= 2;

  string chart\_data\_slice\_id \= 3;

  repeated string row\_ids \= 4;  
  map\<string, string\> field\_filters \= 5;

  double threshold\_value \= 6;  
  double range\_min \= 7;  
  double range\_max \= 8;

  string description \= 9;  
}

---

message Insight {  
  string id \= 1;

  // What kind of insight this is  
  // Examples: "alert", "thumbs\_up", "warning", "lightbulb"  
  string type \= 2;

  // Short, user-facing message  
  string summary \= 3;

  // Optional longer explanation  
  string detail \= 4;

  // Confidence score in \[0,1\]  
  double confidence \= 5;

  // Scope of the insight  
  AnnotationTarget target \= 6;

  // Optional visual evidence  
  repeated Highlight highlights \= 7;

  // Metadata  
  google.protobuf.Timestamp created\_at \= 8;  
  uint32 schema\_version \= 9;  
}

---

message Recommendation {  
  string id \= 1;

  // What kind of action this is  
  // Examples: "fyi", "report", "notification", "export", "share"  
  string type \= 2;

  // Short call-to-action  
  string summary \= 3;

  // Optional explanation or rationale  
  string detail \= 4;

  // Confidence score in \[0,1\]  
  double confidence \= 5;

  // Scope of the recommendation  
  AnnotationTarget target \= 6;

  // Optional payload for the action (app-specific)  
  map\<string, string\> action\_params \= 7;

  // Metadata  
  google.protobuf.Timestamp created\_at \= 8;  
  uint32 schema\_version \= 9;  
}

---

## **4.5 DataBinding (Protobuf – Spec Plane)**

**Responsibility**  
Declares *what data is needed*, not how it is executed.

---

syntax \= "proto3";

package actbi.v1;

message DataBinding {  
  string id \= 1;  
  uint32 version \= 2;

  repeated DataSource sources \= 3;  
  repeated LogicalFilter filters \= 4;  
  repeated Projection projections \= 5;

  uint32 schema\_version \= 6;  
}

This artifact is **SQL / ibis agnostic**.

---

## **4.6 ETL Definition (Stored as Source Code)**

**Responsibility**  
Executable realization of the DataBinding.

Stored as **versioned strings**, not protobuf:

{  
  "etl\_id": "etl\_sales\_v3",  
  "ibis": "sales.filter(...).select(...)",  
  "polars": "df.rename(...).select(...)"  
}

---

## **4.7 OutputSchema (Protobuf – Contract)**

**Responsibility**  
Defines the **shape of materialized data**.

message OutputSchema {  
  string id \= 1;  
  uint32 version \= 2;

  repeated OutputField fields \= 3;  
  repeated string primary\_key \= 4;

  uint32 schema\_version \= 5;  
}

message OutputField {  
  string name \= 1;  
  FieldType type \= 2;  
  FieldRole role \= 3;  
}

---

## **4.8 ChartDataSlice (Protobuf – Metadata Only)**

**Responsibility**  
Lineage \+ pointer to materialized data.

message RefreshPolicy {  
  // Maximum allowed age of the data in seconds.  
  // max\_age\_seconds \= 0 means "must always be fresh".  
  uint32 max\_age\_seconds \= 1;

  // Whether it is acceptable to serve stale data.  
  // If false and data is stale, a refresh MUST occur.  
  bool allow\_stale\_reads \= 2;  
}  
---

message ChartDataSlice {  
  string id \= 1;

  string chart\_id \= 2;  
  uint32 chart\_version \= 3;

  string data\_binding\_id \= 4;  
  uint32 data\_binding\_version \= 5;

  string output\_schema\_id \= 6;

  string json\_uri \= 7;

  string data\_hash \= 8;  
  string schema\_hash \= 9;

  // Explicit freshness \+ staleness policy  
  RefreshPolicy refresh\_policy \= 10;

  google.protobuf.Timestamp generated\_at \= 11;  
}

---

## **4.9 Actual Data (JSON – Data Plane)**

**Responsibility**  
Render-ready facts.

{  
  "schema\_id": "schema\_violin\_sales\_v1",  
  "rows": \[  
    { "row\_id": "r1", "name": "Shoes", "value": 120.0 },  
    { "row\_id": "r2", "name": "Shoes", "value": 95.0 }  
  \]  
}

Properties:

* Strictly conforms to OutputSchema  
* Stable `row_id`  
* Immutable per slice  
* Directly consumable by React charts

# **5\. Data Flow End-to-End (Write, Refresh, Read)**

This section describes how the **CustomerChartStore** is used in practice, covering:

* spec authoring  
* data materialization  
* refresh behavior  
* UI consumption  
* insight highlighting

All examples are concrete and executable in spirit.

## **5.1 Write Path — Authoring & Spec Mutation**

The write path is triggered by **conversational reasoning** and produces **spec artifacts only**.  
No data is fetched unless explicitly requested.

### **Example scenario**

A user asks:

“Show me a violin plot of sales by product category.”

The system produces the following artifacts.

### **5.1.1 Chart (Spec Plane)**

Chart {  
  id: "chart\_violin\_sales\_v1"  
  title: "Sales Distribution by Category"  
  chart\_type: "violin"

  dimensions: \[  
    { field: "name", type: "category" },  
    { field: "value", type: "numeric" }  
  \]

  chart\_data\_slice\_ids: \[\]

  version: 1  
  schema\_version: 1  
}

Properties:

* No embedded data  
* No execution logic  
* Only semantic intent

### **5.1.2 DataBinding (Intent)**

DataBinding {  
  id: "binding\_sales\_by\_category"  
  version: 1

  sources: \[  
    {  
      system: "customer\_datalake"  
      table: "sales"  
    }  
  \]

  projections: \[  
    { field: "product\_category", alias: "name" },  
    { field: "amount", alias: "value" }  
  \]

  schema\_version: 1  
}

The DataBinding declares **what data is required**, not how it is fetched.

### **5.1.3 ETL Definition (Derived Artifact)**

ETL definitions are derived deterministically and stored as **versioned source code strings**.

{  
  "etl\_id": "etl\_sales\_by\_category\_v1",  
  "ibis": "sales.select(product\_category=sales.product\_category, value=sales.amount)",  
  "polars": "df.rename({'product\_category': 'name'}).select(\['name', 'value'\])"  
}

Notes:

* ibis handles data acquisition  
* polars handles shape adaptation  
* ETL code is diffable and cacheable

### **5.1.4 OutputSchema (Data Contract)**

OutputSchema {  
  id: "schema\_violin\_sales\_v1"  
  version: 1

  fields: \[  
    {  
      name: "row\_id"  
      type: STRING  
      role: IDENTIFIER  
      context: "Stable identifier for a single sales record"  
    },  
    {  
      name: "name"  
      type: STRING  
      role: DIMENSION  
      context: "Product category sold"  
    },  
    {  
      name: "value"  
      type: FLOAT  
      role: MEASURE  
      context: "Sales amount in EUR"  
    }  
  \]

  primary\_key: \["row\_id"\]  
  schema\_version: 1  
}

The OutputSchema is the **authoritative shape contract** between data and charts.

### **5.1.5 ChartDataSlice (Registered, Not Materialized)**

ChartDataSlice {  
  id: "slice\_chart\_violin\_sales\_v1"

  chart\_id: "chart\_violin\_sales\_v1"  
  chart\_version: 1

  data\_binding\_id: "binding\_sales\_by\_category"  
  data\_binding\_version: 1

  etl\_id: "etl\_sales\_by\_category\_v1"  
  output\_schema\_id: "schema\_violin\_sales\_v1"

  refresh\_policy: {  
    mode: "sync"  
    ttl\_seconds: 3600  
    refresh\_on\_read: true  
  }

  json\_uri: null  
  generated\_at: null  
}

At this point:

* No data exists yet  
* The slice fully describes *how* it should be refreshed

## **5.2 Data Refresh Path — Deterministic Materialization**

Data refresh is **not agent-driven**.  
It is a deterministic execution of the ETL based on slice metadata.

### **5.2.1 Refresh Decision**

from datetime import datetime, timezone

def should\_refresh\_now(policy, now=None) \-\> bool:  
    if policy is None:  
        return True  \# fail safe

    if now is None:  
        now \= datetime.now(timezone.utc)

    if policy.last\_refreshed\_at is None:  
        return True

    \# Always-fresh policy  
    if policy.max\_age\_seconds \== 0:  
        return True

    age \= (  
        now \- policy.last\_refreshed\_at.replace(tzinfo=timezone.utc)  
    ).total\_seconds()

    \# Clock skew safety  
    if age \< 0:  
        return False

    is\_stale \= age \> policy.max\_age\_seconds

    \# If stale data is not allowed, we MUST refresh  
    if is\_stale and not policy.allow\_stale\_reads:  
        return True

    \# Otherwise refresh only if stale reads are allowed  
    return is\_stale

Key properties:

* Refresh logic is **self-contained**  
* Any process (UI, API, background job) can evaluate it  
* All charts in a dashboard share a consistent refresh boundary

### **5.2.2 ETL Execution**

def materialize\_slice(slice):  
    binding \= load\_data\_binding(slice.data\_binding\_id)  
    etl \= load\_etl(slice.etl\_id)  
    schema \= load\_output\_schema(slice.output\_schema\_id)

    ibis\_expr \= compile\_ibis(binding, etl.ibis)  
    df \= ibis\_expr.execute()

    df \= apply\_polars(df, etl.polars)  
    df \= df.with\_row\_count("row\_id")

    validate\_against\_schema(df, schema)

    return df.to\_dicts()

### **5.2.3 Materialized JSON Data Slice**

{  
  "schema\_id": "schema\_violin\_sales\_v1",  
  "rows": \[  
    { "row\_id": "r1", "name": "Shoes", "value": 120.0 },  
    { "row\_id": "r2", "name": "Shoes", "value": 95.0 },  
    { "row\_id": "r3", "name": "Hats", "value": 40.0 }  
  \]  
}

Properties:

* Immutable  
* Schema-validated  
* Render-ready

### **5.2.4 ChartDataSlice Update**

ChartDataSlice {  
  id: "slice\_chart\_violin\_sales\_v1"

  json\_uri: "db://chart\_data/slice\_chart\_violin\_sales\_v1"  
  data\_hash: "9baf..."  
  schema\_hash: "1a22..."  
  generated\_at: "2025-03-28T14:22:00Z"  
}

## **5.3 Read Path — Context-Aware Data Fetching**

The read path serves chart data to the UI with **context-aware behavior** to support both live dashboards and static conversation history.

**Key distinction:**

* **Dashboard context**: Data refreshes based on TTL and refresh policies (mutable)  
* **Conversation context**: Data is frozen at the moment of request (immutable)

This enables users to revisit conversations and see the exact data that informed the discussion, while dashboards always show current data.

### 5.3.1 Dashboard Context — Live Data

### **Scenario**

User opens a dashboard. Charts should display the latest data, refreshing according to their defined refresh policies.

### **UI Request**

GET /dashboard/{dashboard\_id}

Response:

{  
 "dashboard": {  
 "id": "dashboard\_q1\_sales",  
 "title": "Q1 Sales Overview",  
 ...  
 },  
 "charts": \[  
 {  
 "chart": {  
 "id": "chart\_violin\_sales\_v1",  
 "title": "Sales Distribution by Category",  
 "chart\_type": "violin",  
 ...  
 },  
 "chart\_data\_slice\_id": "slice\_chart\_violin\_sales\_v1"  
 }  
 \]  
 }

### **Data Fetch (Dashboard Context)**

The UI fetches data for each chart:

GET /chart-data/slice\_chart\_violin\_sales\_v1

Or explicitly with context parameter:

GET /chart-data/slice\_chart\_violin\_sales\_v1?context=dashboard

Response:

{  
 "schema\_id": "schema\_violin\_sales\_v1",  
 "rows": \[  
 { "row\_id": "r1", "name": "Shoes", "value": 120.0 },  
 { "row\_id": "r2", "name": "Shoes", "value": 95.0 },  
 { "row\_id": "r3", "name": "Hats", "value": 40.0 }  
 \]  
 }

### **Backend Implementation (Dashboard Context)**

def get\_chart\_data\_dashboard(slice\_id: str) \-\> dict:  
 slice\_metadata \= get\_chart\_data\_slice(slice\_id)  
\# Check if refresh is needed based on policy    
if should\_refresh\_now(slice\_metadata.refresh\_policy):    
    \# Execute ETL to fetch fresh data    
    binding \= load\_data\_binding(slice\_metadata.data\_binding\_id)    
    etl \= load\_etl(slice\_metadata.etl\_id)    
    schema \= load\_output\_schema(slice\_metadata.output\_schema\_id)    
        
    ibis\_expr \= compile\_ibis(binding, etl.ibis)    
    df \= ibis\_expr.execute()  \# ← Fetch from CustomerDataLake    
    df \= apply\_polars(df, etl.polars)    
    df \= df.with\_row\_count("row\_id")    
    validate\_against\_schema(df, schema)    
        
    data \= df.to\_dicts()    
        
    \# Store in dashboard-scoped location    
    store\_json(slice\_metadata.json\_uri, data)    
        
    \# Update metadata    
    update\_slice\_metadata(    
        slice\_id,    
        data\_hash=hash(data),    
        generated\_at=now()    
    )    
        
    return data    
else:    
    \# Serve cached data    
    return load\_json(slice\_metadata.json\_uri)

### **Storage Path (Dashboard Context)**

chart\_data/{chart\_id}/{chart\_version}/{slice\_id}.json

Example:

chart\_data/chart\_violin\_sales\_v1/1/slice\_chart\_violin\_sales\_v1.json

### **Properties (Dashboard Context)**

* **Mutable**: Data refreshed according to refresh\_policy  
* **TTL-based**: max\_age\_seconds determines staleness  
* **Shared**: All dashboard viewers see the same data  
* **Cache eviction**: Can be purged based on storage policies  
* **Consistency**: All charts in a dashboard share the same refresh boundary

### 5.3.2 Conversation Context — Frozen Snapshots

### **Scenario**

User asks: *"Show me a violin plot of sales by product category."*

Agent creates a chart and materializes data. User later revisits this conversation — they should see the **exact same data** that was available when they asked the question.

### **UI Request**

GET /conversation/{conversation\_id}/messages/{message\_id}

Response:

{  
 "message": {  
 "id": "msg\_2025\_03\_28\_456",  
 "conversation\_id": "conv\_2025\_03\_28\_abc123",  
 "text": "Here's the sales distribution by category:",  
 ...  
 },  
 "charts": \[  
 {  
 "chart": {  
 "id": "chart\_violin\_sales\_v1",  
 "title": "Sales Distribution by Category",  
 "chart\_type": "violin",  
 ...  
 },  
 "chart\_data\_slice\_id": "slice\_chart\_violin\_sales\_v1",  
 "conversation\_id": "conv\_2025\_03\_28\_abc123"  
 }  
 \]  
 }

### **Data Fetch (Conversation Context)**

The UI fetches data with conversation context:

GET /chart-data/slice\_chart\_violin\_sales\_v1?context=conversation\&conversation\_id=conv\_2025\_03\_28\_abc123

Response:

{  
 "schema\_id": "schema\_violin\_sales\_v1",  
 "rows": \[  
 { "row\_id": "r1", "name": "Shoes", "value": 120.0 },  
 { "row\_id": "r2", "name": "Shoes", "value": 95.0 },  
 { "row\_id": "r3", "name": "Hats", "value": 40.0 }  
 \]  
 }

**Critical difference:** This data is **frozen**. Even if the dashboard shows different values next week, this conversation will always show these exact values.

### **Backend Implementation (Conversation Context)**

def get\_chart\_data\_conversation(  
 slice\_id: str,  
 conversation\_id: str  
 ) \-\> dict:  
 \# Build conversation-scoped storage path  
 conv\_uri \= f"conversation\_data/{conversation\_id}/{slice\_id}.json"

\# Check if already materialized for this conversation    
if exists(conv\_uri):    
    \# Data already frozen — serve immediately    
    return load\_json(conv\_uri)    
    
\# First time: materialize data using same ETL logic    
slice\_metadata \= get\_chart\_data\_slice(slice\_id)    
    
binding \= load\_data\_binding(slice\_metadata.data\_binding\_id)    
etl \= load\_etl(slice\_metadata.etl\_id)    
schema \= load\_output\_schema(slice\_metadata.output\_schema\_id)    
    
ibis\_expr \= compile\_ibis(binding, etl.ibis)    
df \= ibis\_expr.execute()  \# ← Fetch from CustomerDataLake    
df \= apply\_polars(df, etl.polars)    
df \= df.with\_row\_count("row\_id")    
validate\_against\_schema(df, schema)    
    
data \= df.to\_dicts()    
    
\# Store in conversation-scoped location (immutable)    
store\_json(conv\_uri, data)    
    
\# Optional: track lineage    
create\_conversation\_slice\_record(    
    slice\_id=f"{slice\_id}\_conv\_{conversation\_id}",    
    original\_slice\_id=slice\_id,    
    conversation\_id=conversation\_id,    
    json\_uri=conv\_uri,    
    data\_hash=hash(data),    
    generated\_at=now()    
)    
    
return data

### **Storage Path (Conversation Context)**

conversation\_data/{conversation\_id}/{slice\_id}.json

Example:

conversation\_data/conv\_2025\_03\_28\_abc123/slice\_chart\_violin\_sales\_v1.json

### **Properties (Conversation Context)**

* **Immutable**: Never refreshed, frozen at moment of creation  
* **No TTL**: No expiration, part of conversation history  
* **Isolated**: Each conversation has its own data copy  
* **Preserved**: Retained as long as conversation exists  
* **Historical fidelity**: Users see exactly what the agent saw

### 5.3.3 Unified API Implementation

The public API routes to the appropriate handler based on the `context` parameter:

def get\_chart\_data(  
 slice\_id: str,  
 context: Literal\["conversation", "dashboard"\] \= "dashboard",  
 conversation\_id: Optional\[str\] \= None  
 ) \-\> dict:  
 """  
 Context-aware data fetching.

Args:    
    slice\_id: ChartDataSlice identifier    
    context: "dashboard" (live, refreshable) or "conversation" (frozen)    
    conversation\_id: Required when context="conversation"    
        
Returns:    
    JSON data with schema\_id and rows    
"""    
if context \== "conversation":    
    if conversation\_id is None:    
        raise ValueError(    
            "conversation\_id required for conversation context"    
        )    
    return get\_chart\_data\_conversation(slice\_id, conversation\_id)    
        
elif context \== "dashboard":    
    return get\_chart\_data\_dashboard(slice\_id)    
        
else:    
    raise ValueError(f"Invalid context: {context}")

### **REST Endpoints**

\# Dashboard context (default)  
 GET /chart-data/{slice\_id}  
 GET /chart-data/{slice\_id}?context=dashboard

\# Conversation context  
 GET /chart-data/{slice\_id}?context=conversation\&conversation\_id={conv\_id}

### 5.3.4 Agent Flow for Conversation Context

When an agent creates a chart during a conversation:

\# 1\. Create chart specification  
 chart \= upsert\_chart(chart\_spec)

\# 2\. Create data pipeline artifacts  
 binding \= upsert\_data\_binding(data\_binding\_spec)  
 etl \= upsert\_etl\_definition(etl\_spec)  
 schema \= upsert\_output\_schema(output\_schema\_spec)

\# 3\. Register ChartDataSlice metadata  
 slice\_metadata \= upsert\_chart\_data\_slice(  
 chart\_id=chart.id,  
 data\_binding\_id=binding.id,  
 etl\_id=etl.id,  
 output\_schema\_id=schema.id,  
 refresh\_policy=None \# Optional for conversation context  
 )

\# 4\. Immediately materialize and freeze data  
 \# This executes the ETL and stores data in conversation scope  
 data \= get\_chart\_data(  
 slice\_id=slice\_metadata.id,  
 context="conversation",  
 conversation\_id=current\_conversation\_id  
 )

\# 5\. Return to UI  
 return {  
 "chart": chart,  
 "data": data,  
 "slice\_id": slice\_metadata.id,  
 "conversation\_id": current\_conversation\_id  
 }

**Note:** The agent **always** fetches data immediately in conversation context to freeze the snapshot. This happens during the same request that creates the chart.

### 5.3.5 UI Integration Examples

### **TypeScript: Rendering Conversation Chart**

// Conversation message with embedded chart  
 const chartMessage \= {  
 chart\_id: "chart\_violin\_sales\_v1",  
 slice\_id: "slice\_chart\_violin\_sales\_v1",  
 conversation\_id: "conv\_2025\_03\_28\_abc123"  
 }

// Fetch frozen data from conversation history  
 const response \= await fetch(  
 \`/api/chart-data/${chartMessage.slice\_id}?\` \+  
 \`context=conversation&\` \+  
 \`conversation\_id=${chartMessage.conversation\_id}\`  
 )

const data \= await response.json()

// Render chart with frozen data  
 \<ViolinChart data={data.rows} schema={data.schema\_id} /\>

### **TypeScript: Rendering Dashboard Chart**

// Dashboard chart  
 const dashboardChart \= {  
 chart\_id: "chart\_violin\_sales\_v1",  
 slice\_id: "slice\_chart\_violin\_sales\_v1"  
 }

// Fetch live data (default context)  
 const response \= await fetch(  
 \`/api/chart-data/${dashboardChart.slice\_id}\`  
 )

const data \= await response.json()

// Render chart with potentially refreshed data  
 \<ViolinChart data={data.rows} schema={data.schema\_id} /\>

**UI receives identical response format in both cases:**

{  
 "schema\_id": "schema\_violin\_sales\_v1",  
 "rows": \[  
 { "row\_id": "r1", "name": "Shoes", "value": 120.0 },  
 { "row\_id": "r2", "name": "Shoes", "value": 95.0 },  
 { "row\_id": "r3", "name": "Hats", "value": 40.0 }  
 \]  
 }

The UI:

* passes `rows` directly to the chart component  
* uses `row_id` for evidence highlighting  
* context is transparent to rendering logic  
* same chart components work for both contexts

## **5.3.6 Storage Namespace Separation**

The two contexts use **different storage namespaces** to prevent conflicts and enable independent lifecycle management:

| Context | Storage Path | Lifecycle | Purpose |
| ----- | ----- | ----- | ----- |
| **Dashboard** | \`chart\_data/{chart\_id}/{version}/{slice\_id}.json\` | Mutable, TTL-based, cache eviction | Live analytics |
| **Conversation** | \`conversation\_data/{conversation\_id}/{slice\_id}.json\` | Immutable, permanent archive | Historical record |

This separation ensures:

* No accidental overwrites  
* Clear audit trails  
* Independent retention policies  
* Efficient garbage collection

### 5.3.7 Optional: Conversation Data Lineage Table

For tracking which conversations created which data slices:

CREATE TABLE conversation\_data\_slices (  
 conversation\_id TEXT NOT NULL,  
 slice\_id TEXT NOT NULL,  
 original\_chart\_data\_slice\_id TEXT NOT NULL,  
 json\_uri TEXT NOT NULL,  
 data\_hash TEXT NOT NULL,  
 generated\_at TIMESTAMP NOT NULL,  
 PRIMARY KEY (conversation\_id, slice\_id)  
 )

This enables:

* Listing all data slices in a conversation  
* Tracking data provenance without polluting main ChartDataSlice table  
* Implementing conversation-level cleanup policies  
* Auditing exactly what data was available at conversation time  
* Reconstructing the full context of historical conversations

# **6\. Versioning & Diff Strategy**

This section defines **what gets versioned**, **when versions change**, and **how diffs are produced and interpreted** across all CustomerChartStore artifacts.

The goal is to ensure:

* deterministic evolution  
* low-noise diffs  
* strong auditability  
* LLM-friendly reasoning

## **6.1 Versioned Artifacts**

The following artifacts are **explicitly versioned**:

| Artifact | Versioned | Reason |
| ----- | ----- | ----- |
| Chart | ✅ | Visual intent evolves |
| ChartStack | ✅ | Narrative evolves |
| Dashboard | ✅ | Composition evolves |
| DataBinding | ✅ | Data intent evolves |
| ETL definition | ✅ | Execution logic evolves |
| OutputSchema | ✅ | Data shape evolves |
| ChartDataSlice | ⚠️ metadata only | Points to immutable data |

Actual JSON data slices are **immutable** and **not versioned** directly.

## **6.2 What Triggers a Version Bump**

### **6.2.1 Chart Version Bump**

A Chart version increments when:

* chart\_type changes  
* dimensions change  
* filters change  
* referenced OutputSchema changes  
* referenced ChartDataSlice ID changes

A Chart version **does not** increment when:

* underlying data is refreshed  
* JSON rows change but schema does not

### **6.2.2 DataBinding Version Bump**

A DataBinding version increments when:

* input data sources change  
* joins change  
* projections change  
* logical filters change

It does **not** increment when:

* only data values change  
* execution strategy changes (that is ETL)

### **6.2.3 ETL Version Bump**

An ETL version increments when:

* ibis code changes  
* polars code changes  
* execution semantics change

ETL versioning is **orthogonal** to DataBinding versioning:

* the same DataBinding may have multiple ETL realizations  
* the ETL version is always explicitly referenced by ChartDataSlice

### **6.2.4 OutputSchema Version Bump**

An OutputSchema version increments when:

* fields are added or removed  
* field types change  
* field roles change  
* field context (business meaning) changes  
* primary keys change

OutputSchema versions **must be backward-compatible or explicitly marked incompatible**.

### **6.2.5 ChartDataSlice Versioning**

ChartDataSlice is **immutable once materialized**.

A *new* ChartDataSlice is created when:

* data is refreshed past TTL  
* DataBinding version changes  
* ETL version changes  
* OutputSchema version changes

Existing slices are never mutated.

## **6.3 Canonical Diff Strategy**

All spec artifacts use:

* protobuf as the source of truth  
* canonical JSON serialization  
* textual diffs

### **6.3.1 Canonical Serialization Rules**

* alphabetical key ordering  
* explicit defaults  
* stable list ordering  
* ISO8601 timestamps  
* schema\_version always present

This ensures:

* minimal diffs  
* predictable LLM behavior  
* engineer-readable changes

### **6.3.2 Diff Scope by Artifact**

| Artifact | Diff Focus |
| ----- | ----- |
| Chart | Visual semantics |
| ChartStack | Narrative & grouping |
| Dashboard | Composition & layout |
| DataBinding | Data intent |
| ETL | Execution semantics |
| OutputSchema | Shape & meaning |

JSON data slices are **never diffed**.

## **6.4 LLM-Oriented Diff Interpretation**

Because diffs are:

* textual  
* scoped  
* low-noise

LLMs can reliably:

* explain *what changed*  
* classify changes (visual vs data vs schema)  
* detect semantic drift  
* validate safe evolution

This is a core design goal.

## **6.5 Invariants Guaranteed by Versioning**

* Spec evolution is explicit  
* Data refresh does not pollute diffs  
* Historical dashboards are reproducible  
* Every rendered chart can be reconstructed  
* No “silent” behavioral changes

# **7\. Caching & Performance Strategy**

This section defines **how data is cached**, **when it is refreshed**, and **how performance is preserved**, without embedding OLAP logic inside the CustomerChartStore.

## **7.1 Design Constraints**

* CustomerChartStore is **not** an OLAP engine  
* Data fetching is deterministic and repeatable  
* Performance optimizations must not affect semantics  
* Cache behavior must be observable and explainable

## **7.2 Cache Layers**

### **7.2.1 Data Slice Cache (Primary)**

Each ChartDataSlice represents a **cacheable unit**.

Cache key:

(chart\_id, chart\_version, data\_binding\_version, etl\_version, output\_schema\_version)

Stored as:

* immutable JSON blob  
* referenced by ChartDataSlice

This is the **authoritative cache**.

### **7.2.2 In-Memory / Process Cache (Optional)**

For hot paths:

* recently accessed JSON slices  
* bounded by size and TTL  
* safe to evict

This layer is purely an optimization.

### **7.2.3 HTTP / CDN Cache (Optional)**

JSON slices are:

* immutable  
* content-addressable

They are ideal candidates for:

* HTTP caching  
* CDN distribution

## **7.3 Refresh Policy Execution**

Refresh behavior is driven entirely by `ChartDataSlice.refresh_policy`.

### **Supported modes**

| Mode | Behavior |
| ----- | ----- |
| `sync` | Refresh inline on read |
| `async` | Serve stale, refresh in background |
| `agentic` | Delegate refresh to external process |

The CustomerChartStore does **not** interpret *why* a refresh is needed — only *whether*.

## **7.4 Dashboard-Level Consistency**

When a dashboard is requested:

* all required ChartDataSlices are evaluated together  
* a single refresh boundary is applied  
* either all slices are refreshed or none are

This prevents:

* mixed-time dashboards  
* partial freshness artifacts

## **7.5 Incremental Refresh (Deferred)**

The current design **does not assume incremental updates**.

Reasons:

* simplicity  
* correctness  
* auditability

Incremental refresh can be added later by:

* extending ETL semantics  
* adding slice partitioning  
* without changing APIs or specs

## **7.6 Performance Guarantees**

This strategy guarantees:

* bounded data fetches  
* predictable refresh cost  
* no redundant OLAP queries  
* UI-first latency characteristics  
* scale via cache, not complexity

## **7.7 Explicit Non-Goals**

The CustomerChartStore intentionally does **not**:

* optimize SQL  
* push down predicates  
* manage indexes  
* manage partitions  
* perform cost-based planning

Those belong in the data lake layer.

# **8\. Storage Model**

This section defines **where each artifact lives** and **what each storage layer is responsible for**.

For now, all storage is assumed to be relational.

## **8.1 Relational Database Responsibilities**

The relational database stores:

* All protobuf artifacts (serialized)  
* All version metadata  
* All relationships between artifacts  
* References to JSON data slices

It is the **system of record**.

## **8.2 Artifact Tables (Conceptual)**

| Table | Purpose |
| ----- | ----- |
| `charts` | Chart specs by version |
| `chart_stacks` | Grouping \+ insights |
| `dashboards` | Composition \+ layout |
| `data_bindings` | Data intent |
| `etl_definitions` | ibis \+ polars DSL |
| `output_schemas` | Data contracts |
| `chart_data_slices` | Data slice metadata |
| `conversations` | Reasoning lineage |

Each row is immutable per version.

## **8.3 JSON Data Slice Storage**

JSON data slices:

* Are stored separately from specs  
* Are referenced by `json_uri`  
* Are immutable  
* Conform strictly to an OutputSchema

They may live:

* as JSON/JSONB columns  
* or as blob/object references

The store does not assume a specific physical layout.

## **8.4 Naming & Addressing Conventions**

Recommended addressing scheme:

chart\_data/{chart\_id}/{chart\_version}/{slice\_id}.json

This ensures:

* uniqueness  
* easy debugging  
* predictable cleanup

## **8.5 Referential Integrity**

The store enforces:

* Chart → ChartDataSlice references must exist  
* ChartDataSlice → OutputSchema must exist  
* Highlights → ChartDataSlice must exist

Invalid references are rejected at write time.

# **9\. API Surface (CustomerChartStore)**

This section defines the **logical API**, independent of transport (REST, RPC, in-process).

## **9.1 Read APIs**

### **Fetch by Chart ID**

get\_chart(chart\_id: str, version: int | None) \-\> Chart

### **Fetch by ChartStack ID**

get\_chart\_stack(chart\_stack\_id: str) \-\> ChartStack

### **Fetch by Dashboard ID**

get\_dashboard(dashboard\_id: str) \-\> Dashboard

### **Fetch Chart Data Slice**

get\_chart\_data\_slice(slice\_id: str) \-\> ChartDataSlice

get\_chart\_data(slice\_id: str) \-\> dict  \# JSON rows

## **9.2 Write APIs (Upserts)**

All writes are **explicit upserts with versioning**.

upsert\_chart(chart: Chart) \-\> Chart

upsert\_chart\_stack(stack: ChartStack) \-\> ChartStack

upsert\_dashboard(dashboard: Dashboard) \-\> Dashboard

upsert\_data\_binding(binding: DataBinding) \-\> DataBinding

upsert\_etl\_definition(etl: ETLDefinition) \-\> ETLDefinition

upsert\_output\_schema(schema: OutputSchema) \-\> OutputSchema

upsert\_chart\_data\_slice(slice: ChartDataSlice) \-\> ChartDataSlice

## **9.3 Delete APIs**

Deletes are **soft deletes** by default.

delete\_chart(chart\_id: str, version: int)

delete\_dashboard(dashboard\_id: str)

delete\_chart\_data\_slice(slice\_id: str)

Hard deletes are implementation-specific and audited.

## **9.4 Expected Payload Guarantees**

All API responses guarantee:

* schema\_version present  
* version present  
* deterministic field ordering  
* no embedded data unless explicitly requested

# **10\. Failure Modes & Guardrails**

This section defines how the system fails **safely and predictably**.

## **10.1 Schema Mismatch**

**Scenario**  
JSON data does not conform to OutputSchema.

**Guardrail**

* Validation at materialization time  
* Slice rejected  
* Previous slice remains active

## **10.2 Incompatible Chart / Data Pairing**

**Scenario**  
Chart expects fields not present in OutputSchema.

**Guardrail**

* Validation on ChartSpec update  
* Chart version rejected  
* Clear error surfaced to authoring agent/UI

## **10.3 Partial Data Availability**

**Scenario**  
Some slices refresh successfully, others fail.

**Guardrail**

* Dashboard-level consistency  
* Either all slices refresh or none do  
* UI sees last consistent state

## **10.4 Stale or Missing Data**

**Scenario**  
Data slice is missing or expired.

**Guardrail**

* Serve stale data if allowed by policy  
* Explicit “stale” marker surfaced to UI  
* Optional background refresh

## **10.5 Validation Checkpoints**

Validation occurs at:

* Spec write  
* Schema creation  
* ETL execution  
* Data materialization  
* UI fetch (lightweight)

Failures are **early, explicit, and non-destructive**.

# **APPENDIX 1: INSIGHTS & RECOMMENDATION TYPES**

# **1️⃣ Insight Types**

Insights answer: **“What is happening?”**

They are **observations**, not actions.

### **Recommended Insight Types (v1)**

alert  
warning  
negative  
neutral  
positive  
thumbs\_up  
lightbulb  
anomaly  
trend  
comparison  
confirmation

### **Meaning & UI intent**

| Type | Meaning | Typical UI |
| ----- | ----- | ----- |
| **`alert`** | Critical issue requiring attention | Red badge, high priority |
| **`warning`** | Potential issue or risk | Orange/yellow |
| **`negative`** | Underperformance vs expectation | Downward indicator |
| `neutral` | Informational observation | Subtle |
| **`positive`** | Strong performance | Green |
| `thumbs_up` | Reinforces a good outcome | 👍 / celebratory |
| **`lightbulb`** | Non-obvious insight | 💡 |
| **`anomaly`** | Outlier or unexpected behavior | Highlighted points |
| `trend` | Directional change over time | Arrow / sparkline |
| `comparison` | Difference vs baseline | Side-by-side cue |
| `confirmation` | Confirms a hypothesis | Checkmark |

🔒 **Rule of thumb**  
Insight *type* controls **tone and emphasis**, not behavior.

---

# **2️⃣ Recommendation Types**

Recommendations answer: **“What should I do?”**

They are **calls to action** that the app can execute or assist with.

### **Recommended Recommendation Types (v1)**

fyi  
investigate  
report  
notify  
share  
export  
track  
automate  
adjust  
experiment

### **Meaning & app behavior**

| Type | Meaning | Typical Action |
| ----- | ----- | ----- |
| **`fyi`** | Awareness only | Dismiss / bookmark |
| **`investigate`** | Explore deeper | Drill-down UI |
| **`report`** | Generate report | PDF / slide or weekly email |
| **`notify`** | Alert others | Slack / email |
| **`share`** | Share context | Link / snapshot |
| `export` | Extract data | CSV / Excel |
| `track` | Monitor over time | Create watcher |
| `automate` | Set rule | Scheduled job |
| `adjust` | Change parameter | Edit config |
| **`experiment`** | Try alternative | A/B or scenario |

🔒 **Rule of thumb**  
Recommendation *type* maps to **capabilities your app exposes**.

---

# **3️⃣ Highlight Types**

Highlights answer: **“What should the user look at?”**

They are **visual instructions**, not data.

### **Recommended Highlight Types (v1)**

row  
point  
point\_set  
range  
threshold  
band  
region  
annotation

### **Meaning & visual semantics**

| Type | Meaning | Example |
| ----- | ----- | ----- |
| **`row`** | Single data row | Outlier |
| **`point`** | Single visual point | Spike |
| **`point_set`** | Group of points | All “Shoes” |
| `range` | Continuous interval | Q1–Q3 |
| `threshold` | Reference line | Target \= 100 |
| `band` | Shaded band | Acceptable range |
| `region` | Area of chart | Specific quadrant |
| **`annotation`** | Note or marker | Event label |

🔒 **Rule of thumb**  
Highlight *type* controls **rendering logic**, not semantics.

---

# **4️⃣ How to encode these in protobuf (recommended)**

### **Option A — string enums (flexible, v1-safe)**

string type \= 2; // validated against known values

✔ Easy to extend  
✔ No proto-breaking changes  
✔ LLM-friendly

### **Option B — strict enums (only if you want compile-time safety)**

You *can* introduce enums later once stabilized.

---

# **5️⃣ Validation strategy (important)**

* Validate types **at write time**  
* Reject unknown types unless explicitly allowed  
* Log unknown-but-allowed types for future enum promotion

This lets you:

* evolve fast  
* avoid schema churn  
* still keep discipline

---

# **6️⃣ One-line mental model**

* **Insight type** → *tone*  
* **Recommendation type** → *action*  
* **Highlight type** → *visual emphasis*

[image1]: <data:image/png;base64,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>