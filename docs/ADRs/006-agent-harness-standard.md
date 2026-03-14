# ADR-006: Agent Harness Engineering Standard

| | |
|---|---|
| **Date** | March 2026 |
| **Status** | PROPOSED |
| **Deciders** | Nikos (CTO) |
| **Applies to** | All LangGraph agents via `AgentBuilder` |
| **Supersedes** | None (extends ADR-002, ADR-003) |

---

## 1. Context

The current `AgentBuilder` provides a clean, minimal abstraction: subclasses implement `_build()` to construct a LangGraph `CompiledStateGraph`, and the framework caches compilation via `compile()`. This gives us a consistent entry point for all agents, but it is deliberately unopinionated about what happens inside the graph. Each agent team independently decides how to handle verification, error recovery, constraint enforcement, and state persistence.

The harness engineering literature (OpenAI, Anthropic, LangChain, March 2026) converges on a key finding: agent reliability improves dramatically not from better models, but from better environments. Specifically, five patterns emerge as universal:

1. Task decomposition via structured plans
2. Structured handoff artifacts between sessions
3. Self-verification loops
4. Mechanical constraint enforcement
5. Intentional tool design

Our Agent Architecture document already describes these principles philosophically — TPS-inspired "stop the line" validation, Supervisor as sole state owner, stateless workers returning typed `{ result, validation }` payloads. What we lack is **mechanization**: a way to guarantee these patterns execute in every agent graph, enforced by the framework rather than by developer discipline.

### The Gap Between Architecture and Implementation

The architecture doc says workers "must validate their own outputs" and return `{ passed, warnings, errors }`. But today, validation lives *inside* the worker node — meaning a misbehaving LLM can skip or half-do the validation, and nothing in the graph topology prevents it. The harness engineering approach externalizes validation as **separate, non-skippable graph nodes** that the agent cannot bypass.

Similarly, the architecture doc describes tool bindings with whitelists (`tool_bindings.json`), but tool descriptions are capability-focused ("Executes SQL against the semantic layer") rather than decision-focused ("WHEN TO USE / HOW IT WORKS / DO NOT USE"). The harness literature shows that rich tool descriptions reduce incorrect tool selection measurably.

### Scope of This ADR

This ADR focuses on the **single-agent harness** — patterns 3, 4, and 5 (verification, enforcement, tool design). These apply to every capability agent: QueryBuilder, DataInterpreter, VisualizationDesigner, DataExplorer, SchemaManager, etc.

Patterns 1 and 2 (task decomposition, session handoffs) are **Supervisor-level concerns** that apply to multi-step orchestration. They will be addressed in a separate ADR that extends the Supervisor's graph with structured `TaskPlan` state and `SessionHandoff` protobuf artifacts.

---

## 2. Decision

Extend `AgentBuilder` with four composable harness capabilities. Agents opt in via protected hook methods. The `compile()` method weaves these into the graph topology automatically.

| Capability | Harness Pattern | Builder Hook | Graph Effect |
|---|---|---|---|
| Constraint Enforcement | Pattern 4: Mechanical enforcement | `_constraints()` | Pure Python node after worker, before verification |
| Verification Chain | Pattern 3: Self-verification loops | `_verifiers()` | Ordered nodes: deterministic first, then LLM-based |
| Retry Loop | Pattern 3: Loop back on failure | `_max_retries()` | Conditional edge from last verifier back to worker |
| Tool Contracts | Pattern 5: Intentional tool design | `_tools()` | Validated tool descriptions composed at bind time |

**What we are NOT doing:**

- No task decomposition in individual agents (Supervisor-only concern)
- No session handoff at the capability agent level (Supervisor-only concern)
- No OpenFeature or external flag integration for harness behavior (flags stay in ADR-003's `FlagService`)

---

## 3. Breaking Change: `_build()` Return Type

### The Problem

The current `_build()` returns `CompiledStateGraph` — a compiled, frozen graph. The harness wiring needs to insert nodes and edges *before* compilation. You cannot add nodes to a `CompiledStateGraph`.

```python
# CURRENT — returns compiled graph (frozen, immutable topology)
@abstractmethod
def _build(self) -> CompiledStateGraph:
    ...
```

### The Change

`_build()` must return `StateGraph` (uncompiled). The `compile()` method takes ownership of the compilation step — which it logically should, since "compile" is literally its job.

```python
# NEW — returns uncompiled graph (mutable, harness can weave into it)
@abstractmethod
def _build(self) -> StateGraph:
    ...
```

### Migration

This is a one-line change per agent: remove the `.compile()` call at the end of `_build()`. The framework now calls it.

```python
# BEFORE
class MyAgent(AgentBuilder):
    def _build(self) -> CompiledStateGraph:
        graph = StateGraph(MyState, context_schema=AgentContext)
        graph.add_node("worker", self._work)
        graph.add_edge(START, "worker")
        graph.add_edge("worker", END)
        return graph.compile()   # ← agent compiles

# AFTER
class MyAgent(AgentBuilder):
    def _build(self) -> StateGraph:
        graph = StateGraph(MyState, context_schema=AgentContext)
        graph.add_node("worker", self._work)
        graph.add_edge(START, "worker")
        graph.add_edge("worker", END)
        return graph              # ← framework compiles
```

This is the correct separation of concerns: `_build()` defines the graph structure, `compile()` finalizes it (including harness weaving). The current design where `_build()` returns a compiled graph conflates definition with compilation.

All existing agents must be updated. Since we have a small agent count today, this is low-risk. A `grep -r "graph.compile()"` in the agents directory catches every instance.

---

## 4. The Extended AgentBuilder

### 4.1 Design Principles

1. **Additive, not breaking (beyond the `_build()` return type).** Existing agents that only implement `_build()` continue to work — the harness hooks default to empty lists and zero retries, so `compile()` just compiles the graph as before.
2. **Declarative, not procedural.** Agents declare their constraints and verifiers. The framework wires them into the graph. Developers never manually add verification edges.
3. **Graph topology guarantees execution.** Constraints and verifiers are nodes in the graph, not methods the worker calls internally. The agent cannot skip them.
4. **Protobuf at the boundary.** `ConstraintViolation` and `VerificationResult` are protobuf messages, consistent with our two-plane architecture.
5. **Composable with existing patterns.** Callbacks (Langfuse + PostHog via `CallbackFactory`) continue to be injected via `config`. Constraints and verifiers are orthogonal to observability.

### 4.2 The Base Class

```python
"""Base builder infrastructure for LangGraph-based agents.

All new agents should extend AgentBuilder and implement _build()
to construct their agent graph. Optionally override harness hooks
to declare constraints, verifiers, and tool contracts.

Consumers call compile() to obtain a standard CompiledStateGraph
that supports the full LangChain Runnable API.

Example::

    class QueryBuilderAgent(AgentBuilder):
        def _build(self) -> StateGraph:
            graph = StateGraph(QueryBuilderState, context_schema=AgentContext)
            graph.add_node("generate_sql", self._generate_sql, metadata={"role": "worker"})
            graph.add_edge(START, "generate_sql")
            graph.add_edge("generate_sql", END)
            return graph

        def _constraints(self) -> list[Constraint]:
            return [SchemaFieldExistence(), TenantIsolation()]

        def _verifiers(self) -> list[Verifier]:
            return [SQLSyntaxVerifier(), IntentAlignmentVerifier()]

        def _max_retries(self) -> int:
            return 2

    agent = QueryBuilderAgent()
    graph = agent.compile()
    result = await graph.ainvoke(state, context=ctx)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, final

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.harness.constraints import Constraint
from agents.harness.verifiers import Verifier
from agents.harness.tools import ToolContract
from agents.harness.wiring import weave_harness


class AgentBuilder(ABC):
    """Base builder for all LangGraph-based agents.

    Subclasses implement _build() to define the agent graph and
    optionally override harness hooks to declare constraints,
    verifiers, retry policy, and tool contracts.

    The compile() method weaves harness nodes into the graph
    topology automatically, then compiles. Result is cached.
    """

    def __init__(self) -> None:
        self._compiled: CompiledStateGraph | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if "compile" in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must not override compile(). "
                "Implement _build() instead."
            )

    # ── Core hook (required) ─────────────────────────────

    @abstractmethod
    def _build(self) -> StateGraph:
        """Construct and return the uncompiled agent graph.

        Subclasses must implement this method. It is called once
        by compile(). The framework handles compilation after
        weaving in harness nodes.

        Returns:
            An uncompiled StateGraph. Do NOT call .compile() —
            the framework does that.
        """
        ...

    # ── Harness hooks (optional) ─────────────────────────

    def _constraints(self) -> list[Constraint]:
        """Pure Python invariant checks run after the worker node.

        Constraints never call an LLM. They inspect state and
        return ConstraintViolation objects with fix instructions.

        Override to declare domain-specific invariants.
        Default: empty list (no constraint enforcement).
        """
        return []

    def _verifiers(self) -> list[Verifier]:
        """Verification nodes run after constraint enforcement.

        Deterministic verifiers should come before LLM-based
        verifiers in the returned list. The framework respects
        this ordering and sorts by VerifierKind as a safety net.

        Override to declare quality checks.
        Default: empty list (no verification).
        """
        return []

    def _max_retries(self) -> int:
        """Maximum retry loops when verification fails.

        When a constraint or verifier fails and retries remain,
        the framework routes back to the worker node with issues
        injected into state. The worker prompt should read these
        issues and self-correct.

        Override to set retry policy.
        Default: 0 (no retries — fail immediately).
        """
        return 0

    def _tools(self) -> list[ToolContract]:
        """Tool contracts with structured decision guidance.

        Each ToolContract must declare when_to_use, how_it_works,
        and do_not_use. The framework composes these into the
        LangChain tool description at bind time and validates
        that all three fields are substantive.

        Override to declare tool bindings with rich descriptions.
        Default: empty list (tools bound however _build() sets them).
        """
        return []

    # ── Public API (sealed) ──────────────────────────────

    @final
    def compile(self) -> CompiledStateGraph:
        """Compile the agent graph with harness wiring (cached).

        This is the public entry-point for obtaining the executable
        agent. On first call it:

        1. Calls _build() to get the uncompiled StateGraph
        2. Calls weave_harness() to insert constraint, verification,
           and retry nodes based on declared hooks
        3. Compiles the woven graph
        4. Caches and returns the CompiledStateGraph

        This method is non-overridable — subclasses must implement
        _build() and harness hooks instead.
        """
        if self._compiled is None:
            graph = self._build()
            self._compiled = weave_harness(
                graph=graph,
                constraints=self._constraints(),
                verifiers=self._verifiers(),
                max_retries=self._max_retries(),
                tool_contracts=self._tools(),
            )
        return self._compiled

    def reset(self) -> None:
        """Clear the cached compilation.

        Useful in testing or when the builder's configuration
        has changed and you need a fresh graph.
        """
        self._compiled = None
```

### 4.3 What Changed From the Current Builder

| Aspect | Before | After | Why |
|---|---|---|---|
| `_build()` return type | `CompiledStateGraph` | `StateGraph` | Framework needs mutable graph to insert harness nodes |
| `compile()` internals | Calls `_build()`, caches | Calls `_build()` → `weave_harness()` → `.compile()`, caches | Compilation is `compile()`'s responsibility, not `_build()`'s |
| Harness hooks | N/A | `_constraints()`, `_verifiers()`, `_max_retries()`, `_tools()` | Declarative harness capabilities |
| Imports | None beyond langgraph | Adds harness module imports | New dependencies |

---

## 5. Constraint Enforcement

Constraints are pure Python checks that validate domain invariants after a worker produces output. They never call an LLM. They run as a single graph node that the topology guarantees will execute. They produce structured violation messages that include both the problem and a remediation instruction for the worker if it retries.

### 5.1 The Constraint Protocol

```python
from dataclasses import dataclass
from typing import Protocol, Any


@dataclass(frozen=True)
class ConstraintViolation:
    """A single constraint violation with remediation.

    The fix_instruction is written for the LLM worker — it should
    be specific enough that the worker can self-correct without
    guessing. This is the OpenAI pattern of error messages as
    agent instructions.
    """
    constraint_name: str
    message: str
    fix_instruction: str


class Constraint(Protocol):
    """Protocol for domain-specific invariant checks.

    Constraints are pure functions: no LLM calls, no I/O,
    no side effects. They inspect state and return violations
    with actionable fix instructions.

    Every constraint must have a unique name for observability
    and eval metrics.
    """
    name: str

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        """Return violations found, or empty list if all invariants hold."""
        ...
```

### 5.2 Protobuf Definition

```protobuf
// packages/proto/actbi/v1/harness.proto

syntax = "proto3";
package actbi.v1;

message ConstraintViolation {
  string constraint_name = 1;
  string message = 2;
  string fix_instruction = 3;
}

message ConstraintResult {
  repeated ConstraintViolation violations = 1;
  bool passed = 2;
}
```

### 5.3 Examples for ActBI Agents

#### QueryBuilder Constraints

```python
class SchemaFieldExistence:
    """Every field referenced in generated SQL must exist
    in the XLake schema slice provided to the agent."""
    name = "schema_field_existence"

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        violations = []
        sql_fields = state.get("parsed_sql_fields", [])
        schema_fields = {
            f["name"] for f in state.get("schema_slice", {}).get("fields", [])
        }
        for field in sql_fields:
            if field not in schema_fields:
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"Field '{field}' not found in schema slice.",
                    fix_instruction=(
                        f"FIX: Remove '{field}' from SQL or use one of: "
                        f"{sorted(schema_fields)[:10]}. Check XLake semantic "
                        f"layer for aliases or joins that expose this field."
                    ),
                ))
        return violations


class TenantIsolation:
    """Generated SQL must not reference tables outside the
    tenant's authorized schema namespace."""
    name = "tenant_isolation"

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        violations = []
        tenant_schemas = set(state.get("authorized_schemas", []))
        referenced_schemas = set(state.get("parsed_sql_schemas", []))
        unauthorized = referenced_schemas - tenant_schemas
        if unauthorized:
            violations.append(ConstraintViolation(
                constraint_name=self.name,
                message=f"SQL references unauthorized schemas: {unauthorized}.",
                fix_instruction=(
                    f"FIX: Restrict query to schemas: {sorted(tenant_schemas)}. "
                    f"The schemas {unauthorized} belong to other tenants or "
                    f"are system-internal. This is a security boundary."
                ),
            ))
        return violations


class SQLInjectionGuard:
    """Reject SQL containing dangerous patterns."""
    name = "sql_injection_guard"

    FORBIDDEN = ["DROP ", "DELETE ", "TRUNCATE ", "ALTER ", "INSERT ", "UPDATE ", "GRANT ", "REVOKE "]

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        sql = state.get("generated_sql", "").upper()
        violations = []
        for pattern in self.FORBIDDEN:
            if pattern in sql:
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"SQL contains forbidden pattern: {pattern.strip()}.",
                    fix_instruction=(
                        "FIX: ActBI only generates read-only queries (SELECT). "
                        "Re-generate the query using only SELECT statements. "
                        "Data modifications are handled by the Data Platform pipelines."
                    ),
                ))
        return violations
```

#### DataInterpreter Constraints

```python
class InsightDataAlignment:
    """Claims in generated insights must be directionally
    consistent with the actual data slice."""
    name = "insight_data_alignment"

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        violations = []
        for insight in state.get("insights", []):
            direction = insight.get("direction")
            actual_delta = state.get("data_slice", {}).get("delta_pct")
            if direction and actual_delta is not None:
                if direction == "increase" and actual_delta < 0:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=(
                            f"Insight claims 'increase' but actual delta "
                            f"is {actual_delta:.1f}%."
                        ),
                        fix_instruction=(
                            "FIX: Re-examine data_slice.delta_pct. Either "
                            "correct the direction to 'decrease' or verify "
                            "you are reading the correct metric and time range."
                        ),
                    ))
                elif direction == "decrease" and actual_delta > 0:
                    violations.append(ConstraintViolation(
                        constraint_name=self.name,
                        message=(
                            f"Insight claims 'decrease' but actual delta "
                            f"is +{actual_delta:.1f}%."
                        ),
                        fix_instruction=(
                            "FIX: Re-examine data_slice.delta_pct. Either "
                            "correct the direction to 'increase' or verify "
                            "you are reading the correct metric and time range."
                        ),
                    ))
        return violations


class ConfidenceScoreBounds:
    """Insight confidence scores must be in [0, 1]."""
    name = "confidence_score_bounds"

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        violations = []
        for insight in state.get("insights", []):
            conf = insight.get("confidence")
            if conf is not None and not (0.0 <= conf <= 1.0):
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=f"Confidence {conf} is outside [0, 1].",
                    fix_instruction=(
                        "FIX: Normalize confidence to [0, 1]. If the raw "
                        "score is a percentage, divide by 100. If it's a "
                        "logit, apply sigmoid."
                    ),
                ))
        return violations
```

#### VisualizationDesigner Constraints

```python
class EncodingDataTypeMatch:
    """Chart encoding channels must match the data type of
    the mapped field (e.g., categorical field not on numeric axis)."""
    name = "encoding_data_type_match"

    def check(self, state: dict[str, Any]) -> list[ConstraintViolation]:
        violations = []
        chart_spec = state.get("chart_spec", {})
        schema_fields = {
            f["name"]: f["type"]
            for f in state.get("schema_slice", {}).get("fields", [])
        }
        for encoding in chart_spec.get("encodings", []):
            field_name = encoding.get("field")
            channel = encoding.get("channel")  # x, y, color, size
            field_type = schema_fields.get(field_name)
            if field_type == "categorical" and channel in ("y", "size"):
                violations.append(ConstraintViolation(
                    constraint_name=self.name,
                    message=(
                        f"Field '{field_name}' is categorical but mapped "
                        f"to numeric channel '{channel}'."
                    ),
                    fix_instruction=(
                        f"FIX: Map '{field_name}' to 'x' or 'color' channel "
                        f"(categorical-appropriate). Use a numeric measure "
                        f"for the '{channel}' channel."
                    ),
                ))
        return violations
```

---

## 6. Verification Chain

Verifiers check whether the agent's output is correct and complete. Unlike constraints (which check invariants are not violated), verifiers assess output quality against the task specification. They come in two kinds:

- **Deterministic verifiers** — pure Python, run first, cheap and fast
- **LLM-based verifiers** — use a separate LLM call, run second, catch semantic issues

The ordering matters: deterministic checks are milliseconds; there is no point spending tokens on an LLM verifier if the output fails basic structural checks.

### 6.1 The Verifier Protocol

```python
from enum import Enum


class VerifierKind(Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a single verifier."""
    verifier_name: str
    passed: bool
    issues: list[str]


class Verifier(Protocol):
    """Protocol for output quality checks.

    Deterministic verifiers run first (fast, cheap).
    LLM verifiers run second (slower, catch semantic issues).
    """
    name: str
    kind: VerifierKind

    async def verify(self, state: dict[str, Any]) -> VerificationResult:
        ...
```

### 6.2 Protobuf Definition

```protobuf
// packages/proto/actbi/v1/harness.proto (continued)

enum VerifierKind {
  VERIFIER_KIND_UNSPECIFIED = 0;
  VERIFIER_KIND_DETERMINISTIC = 1;
  VERIFIER_KIND_LLM = 2;
}

message VerificationResult {
  string verifier_name = 1;
  bool passed = 2;
  repeated string issues = 3;
  VerifierKind kind = 4;
}

message HarnessOutcome {
  ConstraintResult constraint_result = 1;
  repeated VerificationResult verification_results = 2;
  string status = 3;  // "passed" | "needs_fix" | "failed"
  uint32 retry_count = 4;
}
```

### 6.3 Examples

#### QueryBuilder — Deterministic Verifier

```python
class SQLSyntaxVerifier:
    """Parse generated SQL with sqlglot to catch syntax errors
    before any LLM-based review."""
    name = "sql_syntax"
    kind = VerifierKind.DETERMINISTIC

    async def verify(self, state: dict[str, Any]) -> VerificationResult:
        sql = state.get("generated_sql", "")
        try:
            import sqlglot
            sqlglot.parse(sql)
            return VerificationResult(
                verifier_name=self.name, passed=True, issues=[]
            )
        except sqlglot.errors.ParseError as e:
            return VerificationResult(
                verifier_name=self.name,
                passed=False,
                issues=[f"SQL syntax error: {e}. Re-generate the query."],
            )
```

#### QueryBuilder — LLM Verifier

```python
class IntentAlignmentVerifier:
    """LLM check: does the generated SQL actually answer
    the user's question?"""
    name = "intent_alignment"
    kind = VerifierKind.LLM

    async def verify(self, state: dict[str, Any]) -> VerificationResult:
        verdict = await llm.with_structured_output(
            VerificationResult
        ).ainvoke(
            f"""You are a SQL reviewer for a BI platform.

            USER QUESTION: {state["user_question"]}
            GENERATED SQL: {state["generated_sql"]}
            AVAILABLE SCHEMA: {state["schema_slice"]}

            Check:
            1. Does the SQL answer the user's question?
            2. Are the correct measures and dimensions selected?
            3. Are filters and time ranges appropriate?

            Return passed=True if the SQL is correct, or
            passed=False with specific issues to fix."""
        )
        return verdict
```

#### DataInterpreter — Deterministic Verifier

```python
class InsightStructureVerifier:
    """Verify insights have required fields and valid structure
    before LLM quality review."""
    name = "insight_structure"
    kind = VerifierKind.DETERMINISTIC

    REQUIRED_FIELDS = {"summary", "confidence", "direction"}

    async def verify(self, state: dict[str, Any]) -> VerificationResult:
        issues = []
        for i, insight in enumerate(state.get("insights", [])):
            missing = self.REQUIRED_FIELDS - set(insight.keys())
            if missing:
                issues.append(
                    f"Insight {i} missing fields: {missing}. "
                    f"Add them to the insight output."
                )
        return VerificationResult(
            verifier_name=self.name,
            passed=len(issues) == 0,
            issues=issues,
        )
```

---

## 7. Tool Contracts

Tool contracts extend the existing `tool_bindings.json` with structured decision guidance. Every tool exposed to an agent must declare when to use it, how it works, and when not to use it. The framework validates these at compile time and composes them into the LangChain tool description.

### 7.1 The ToolContract Model

```python
from pydantic import BaseModel, model_validator
from typing import Any


class ToolContract(BaseModel):
    """Structured tool description for agent reasoning.

    All three guidance fields are required. The framework
    composes them into the LangChain tool description at
    bind time. Validation ensures guidance is substantive,
    not placeholder text.
    """
    name: str
    when_to_use: str
    how_it_works: str
    do_not_use: str
    tool_callable: Any  # The actual @tool function

    @model_validator(mode="after")
    def validate_guidance(self):
        for field in ("when_to_use", "how_it_works", "do_not_use"):
            value = getattr(self, field)
            if len(value.strip()) < 20:
                raise ValueError(
                    f"ToolContract.{field} must be substantive (>20 chars). "
                    f"Got: '{value}'. Provide real decision guidance."
                )
        return self

    def compose_description(self) -> str:
        """Compose the three guidance fields into a single
        tool description for LangChain binding."""
        return (
            f"{self.when_to_use}\n\n"
            f"HOW IT WORKS: {self.how_it_works}\n\n"
            f"DO NOT USE: {self.do_not_use}"
        )
```

### 7.2 Example: XLake Data Client Tools

```python
semantic_knowledge_fetch_contract = ToolContract(
    name="semantic_knowledge_fetch",
    when_to_use=(
        "Use for conceptual queries where you need business meaning, "
        "KPI definitions, relationship context, or domain concepts. "
        "Ideal when the user's question involves business terms that "
        "may not match raw field names."
    ),
    how_it_works=(
        "Embeds the query and runs cosine similarity against the "
        "CustomerContextStore (Qdrant). Returns semantic matches "
        "with confidence scores. Results include KPIs, business "
        "definitions, and relationship metadata."
    ),
    do_not_use=(
        "Do NOT use for raw schema lookups (use schema_fetch instead). "
        "Do NOT use for data retrieval (use sql_execute instead). "
        "Do NOT use when you already have the exact field name — "
        "semantic search adds latency for no benefit in that case."
    ),
    tool_callable=semantic_knowledge_fetch,
)


schema_fetch_contract = ToolContract(
    name="schema_fetch",
    when_to_use=(
        "Use when you need exact table/column names, data types, "
        "or join paths. Use after intent classification to ground "
        "the query plan in the actual schema."
    ),
    how_it_works=(
        "Reads from XLake's structural layer (Supabase/Postgres). "
        "Returns tables, fields, types, and explicit relationships. "
        "Results are tenant-scoped via RLS."
    ),
    do_not_use=(
        "Do NOT use for meaning or definitions (use semantic_knowledge_fetch). "
        "Do NOT use to execute queries (use sql_execute). "
        "Do NOT call repeatedly for the same schema slice within one task."
    ),
    tool_callable=schema_fetch,
)
```

---

## 8. Graph Wiring: How `weave_harness()` Works

The `weave_harness()` function converts declarative hooks into graph topology. It receives the uncompiled `StateGraph` from `_build()`, inserts harness nodes, and compiles.

### 8.1 The Wiring Algorithm

```python
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph


def weave_harness(
    graph: StateGraph,
    constraints: list[Constraint],
    verifiers: list[Verifier],
    max_retries: int,
    tool_contracts: list[ToolContract],
) -> CompiledStateGraph:
    """Weave harness nodes into the graph and compile.

    If no harness hooks are declared (all defaults), this
    just compiles the graph unchanged — zero overhead for
    agents that don't opt in.
    """
    has_harness = constraints or verifiers

    if not has_harness:
        # No harness declared — compile as-is
        if tool_contracts:
            _apply_tool_contracts(graph, tool_contracts)
        return graph.compile()

    # 1. Find the worker node (tagged with metadata role="worker")
    worker_node = _find_worker_node(graph)

    # 2. Remove the worker → END edge (we'll re-route through harness)
    _remove_edge(graph, worker_node, END)

    # 3. Insert constraint enforcement node
    if constraints:
        graph.add_node(
            "enforce_constraints",
            _make_constraint_node(constraints),
        )
        graph.add_edge(worker_node, "enforce_constraints")
        last_node = "enforce_constraints"
    else:
        last_node = worker_node

    # 4. Insert verification nodes (deterministic first, then LLM)
    sorted_verifiers = sorted(verifiers, key=lambda v: v.kind.value)
    for verifier in sorted_verifiers:
        node_name = f"verify_{verifier.name}"
        graph.add_node(node_name, _make_verifier_node(verifier))
        graph.add_edge(last_node, node_name)
        last_node = node_name

    # 5. Add retry conditional edge from last verifier
    if max_retries > 0:
        graph.add_conditional_edges(
            last_node,
            _make_retry_router(max_retries, worker_node),
        )
    else:
        graph.add_conditional_edges(
            last_node,
            _make_pass_fail_router(),
        )

    # 6. Apply tool contracts
    if tool_contracts:
        _apply_tool_contracts(graph, tool_contracts)

    return graph.compile()
```

### 8.2 The Retry Router

```python
def _make_retry_router(max_retries: int, worker_node: str):
    """Return a router function that loops back to worker on failure
    if retries remain, or routes to END."""

    def router(state: dict[str, Any]) -> str:
        # Check if any constraint or verifier failed
        has_violations = bool(state.get("constraint_violations"))
        has_failures = any(
            not r.passed for r in state.get("verification_results", [])
        )

        if (has_violations or has_failures) and state.get("retry_count", 0) < max_retries:
            # Flatten all issues into retry_issues for the worker prompt
            issues = [v.fix_instruction for v in state.get("constraint_violations", [])]
            issues += [
                issue
                for r in state.get("verification_results", [])
                if not r.passed
                for issue in r.issues
            ]
            state["retry_issues"] = issues
            state["retry_count"] = state.get("retry_count", 0) + 1
            state["harness_status"] = "needs_fix"
            return worker_node

        if has_violations or has_failures:
            state["harness_status"] = "failed"
        else:
            state["harness_status"] = "passed"
        return END

    return router
```

### 8.3 Resulting Graph Topology

For an agent with constraints, two verifiers (one deterministic, one LLM), and `max_retries=2`:

```
START
  → [core graph nodes from _build()]
  → worker (tagged)
  → enforce_constraints          ← pure Python, no LLM
  → verify_sql_syntax            ← deterministic
  → verify_intent_alignment      ← LLM-based
  → [if failed AND retries < 2]  → worker (with retry_issues in state)
  → [if passed OR retries = 2]   → END
```

**Critical detail:** When the worker loops back, `state["retry_issues"]` contains the flattened fix instructions from both constraints and verifiers. The worker prompt must read this field and address the issues specifically. The framework handles state injection; the agent developer handles prompt design to consume it.

---

## 9. Harness State Schema

Every agent state that participates in the harness extends a common base. This ensures constraint violations, verification results, and retry counts are available to the framework wiring without requiring each agent to define them.

```python
class HarnessState(TypedDict, total=False):
    """Mixed into every harnessed agent's state.

    Fields are optional (total=False) so agents that don't
    use the harness don't need to initialize them. The
    framework populates them during harness execution.
    """
    constraint_violations: list[ConstraintViolation]
    verification_results: list[VerificationResult]
    harness_status: str          # "passed" | "needs_fix" | "failed"
    retry_count: int
    retry_issues: list[str]      # Flattened fix instructions for worker prompt
```

Agent state classes mix this in:

```python
class QueryBuilderState(HarnessState):
    """State for the QueryBuilder agent."""
    user_question: str
    schema_slice: dict
    generated_sql: str
    parsed_sql_fields: list[str]
    parsed_sql_schemas: list[str]
    authorized_schemas: list[str]
    # ... agent-specific fields
```

**Integration with protobuf:** `ConstraintViolation` and `VerificationResult` get protobuf definitions (Section 5.2 / 6.2). Internal state uses Python dataclasses; serialization to protobuf happens at the `translate_event()` boundary, consistent with ADR-003's SSE streaming pattern. Conversation event logs capture `HarnessOutcome` as a first-class event.

---

## 10. Integration with the Evaluation Framework (ADR-002)

Harness outcomes are first-class evaluation data. Constraint and verification results surface automatically in the evaluation pipeline.

### 10.1 Automatic Metrics

The following metrics are derived automatically from `HarnessState` for every harnessed agent run:

| Metric | Derivation | Signal |
|---|---|---|
| `constraint_pass_rate` | % of runs with zero violations | Domain rule coverage quality |
| `verification_pass_rate` | % of runs where all verifiers pass on first attempt | Output quality |
| `retry_rate` | % of runs requiring at least one retry | Worker prompt / tool design quality |
| `mean_retries_to_pass` | Avg retries before pass (among runs that eventually pass) | Self-correction effectiveness |
| `constraint_violation_by_name` | Breakdown per constraint name | Identifies which invariants fail most |
| `verification_failure_by_name` | Breakdown per verifier name | Identifies which quality checks fail most |

### 10.2 Eval Config Extension

```yaml
# evals/configs/query_builder.yaml
name: query_builder_eval
agent: agents.query_builder:QueryBuilderAgent
dataset: query_builder

models:
  - anthropic:claude-sonnet-4-20250514

assert:
  # Standard assertions from ADR-002
  - type: not-null
    field: generated_sql
  - type: latency-budget
    max_seconds: 8

  # Harness assertions (new)
  - type: harness-constraints-pass
  - type: harness-verification-pass
  - type: harness-retries-max
    max: 2
```

### 10.3 Workflow Milestone Integration

For Supervisor-level evaluations, harness outcomes from sub-agents become milestone data:

```yaml
- name: revenue_analysis
  workflow: supervisor_pipeline
  inputs:
    user_message: "Why did revenue drop in Q3?"
  milestones:
    - agent: query_builder
      assert:
        - type: harness-constraints-pass
        - type: harness-verification-pass
    - agent: data_interpreter
      assert:
        - type: harness-constraints-pass
```

---

## 11. Observability Integration (ADR-003)

Harness events follow the ADR-003 pattern: `EventBus` is the sole PostHog capture caller, agents import neither SDK. Harness nodes emit events through the existing callback infrastructure.

### 11.1 Event Taxonomy

| Event | Source | Properties |
|---|---|---|
| `agent_constraint_violation` | `enforce_constraints` node | `agent_name`, `constraint_name`, `message`, `fix_instruction` |
| `agent_verification_failed` | `verify_*` node | `agent_name`, `verifier_name`, `kind`, `issues[]` |
| `agent_retry_loop` | retry router | `agent_name`, `retry_count`, `trigger` (constraint\|verifier) |
| `agent_harness_passed` | final verifier / router | `agent_name`, `total_retries`, `constraints_checked`, `verifiers_run` |

Events use the `agent_` domain prefix for consistency with the existing `conversation_`, `visualization_`, and `decision_` prefixes. They flow through `EventBus` methods.

### 11.2 Langfuse Trace Integration

Harness nodes appear as child spans in the Langfuse trace for the agent run. The trace waterfall shows:

```
agent_run (parent span)
  ├── generate_sql (worker)          450ms
  ├── enforce_constraints             12ms
  ├── verify_sql_syntax                8ms
  ├── verify_intent_alignment        380ms  ← LLM call visible
  ├── [retry: intent misalignment]
  ├── generate_sql (retry 1)         520ms
  ├── enforce_constraints              11ms
  ├── verify_sql_syntax                7ms
  └── verify_intent_alignment        350ms  ← passed
```

This uses the existing `CallbackFactory.for_run()` pattern — harness nodes receive the same callback list as worker nodes via `config={"callbacks": ...}`.

---

## 12. Concrete Agent Example: Full QueryBuilder

Putting it all together — this is what a fully harnessed agent looks like:

```python
from agents.base import AgentBuilder
from agents.harness.constraints import (
    SchemaFieldExistence, SQLInjectionGuard, TenantIsolation,
)
from agents.harness.verifiers import (
    SQLSyntaxVerifier, SchemaConsistencyVerifier, IntentAlignmentVerifier,
)
from agents.harness.tools import ToolContract
from agents.query_builder.tools import (
    sql_execute_contract, schema_fetch_contract,
    semantic_knowledge_fetch_contract,
)


class QueryBuilderAgent(AgentBuilder):

    def _build(self) -> StateGraph:
        """Core graph: just the worker logic.

        The framework adds constraint, verification, and retry
        nodes around this automatically.
        """
        graph = StateGraph(QueryBuilderState, context_schema=AgentContext)
        graph.add_node(
            "generate_sql",
            self._generate_sql,
            metadata={"role": "worker"},  # ← tag for harness wiring
        )
        graph.add_edge(START, "generate_sql")
        graph.add_edge("generate_sql", END)
        return graph

    def _constraints(self) -> list[Constraint]:
        return [
            SchemaFieldExistence(),
            SQLInjectionGuard(),
            TenantIsolation(),
        ]

    def _verifiers(self) -> list[Verifier]:
        return [
            SQLSyntaxVerifier(),              # deterministic — runs first
            SchemaConsistencyVerifier(),       # deterministic
            IntentAlignmentVerifier(),         # LLM — runs last
        ]

    def _max_retries(self) -> int:
        return 2

    def _tools(self) -> list[ToolContract]:
        return [
            sql_execute_contract,
            schema_fetch_contract,
            semantic_knowledge_fetch_contract,
        ]

    async def _generate_sql(self, state: QueryBuilderState, context: AgentContext):
        """The worker node.

        On first invocation: generates SQL from user question + schema.
        On retry: reads state['retry_issues'] and self-corrects.
        """
        retry_issues = state.get("retry_issues", [])

        if retry_issues:
            # Self-correction prompt
            prompt = (
                f"Your previous SQL had issues:\n"
                + "\n".join(f"- {issue}" for issue in retry_issues)
                + f"\n\nOriginal question: {state['user_question']}"
                f"\nSchema: {state['schema_slice']}"
                f"\nPrevious SQL: {state['generated_sql']}"
                f"\n\nGenerate a corrected SQL query."
            )
        else:
            # First attempt
            prompt = (
                f"Generate SQL for this question: {state['user_question']}"
                f"\nSchema: {state['schema_slice']}"
            )

        result = await llm.with_structured_output(SQLOutput).ainvoke(prompt)

        return {
            "generated_sql": result.sql,
            "parsed_sql_fields": result.referenced_fields,
            "parsed_sql_schemas": result.referenced_schemas,
            # Clear harness state for fresh verification
            "constraint_violations": [],
            "verification_results": [],
            "retry_issues": [],
        }
```

The developer writes **one node** (`_generate_sql`) and declares three constraints, three verifiers, and three tool contracts. The compiled graph has seven nodes and a retry loop, but the developer never writes a single edge for any of that.

---

## 13. Rollout Plan

### Phase 1: Foundation (Week 1–2)

- Implement `Constraint` and `Verifier` protocols
- Implement `ToolContract` Pydantic model
- Add protobuf definitions to `packages/proto/actbi/v1/harness.proto`
- Implement `weave_harness()` graph wiring function
- Extend `AgentBuilder` with harness hooks
- Migrate existing agents: change `_build()` return type from `CompiledStateGraph` to `StateGraph` (remove `.compile()` calls)
- Unit tests: verify graph topology for various hook combinations (no hooks, constraints only, full harness, retry loop)

### Phase 2: QueryBuilder Pilot (Week 3)

- Implement `SchemaFieldExistence`, `TenantIsolation`, `SQLInjectionGuard` constraints
- Implement `SQLSyntaxVerifier`, `SchemaConsistencyVerifier`, `IntentAlignmentVerifier`
- Define tool contracts for SQL execution, schema fetch, semantic search
- Measure: `constraint_pass_rate`, `verification_pass_rate`, `retry_rate` against existing eval suite
- Compare SQL correctness before/after harness

### Phase 3: DataInterpreter + VisualizationDesigner (Week 4–5)

- Apply harness to DataInterpreter: `InsightDataAlignment`, `ConfidenceScoreBounds` constraints; `InsightStructureVerifier`, `InsightCompletenessVerifier`
- Apply harness to VisualizationDesigner: `EncodingDataTypeMatch`, `ChartSpecCompleteness` constraints
- Integrate harness metrics into PostHog dashboards and Langfuse trace views
- Add `harness-constraints-pass` and `harness-verification-pass` assertion types to eval framework

### Phase 4: Framework Standard (Week 6)

- Document harness patterns in agent developer guide
- Add constraint/verifier templates to agent scaffolding
- Establish convention: every new agent ships with at least one constraint and one deterministic verifier
- Design follow-up ADR for Supervisor-level harness (task decomposition + session handoffs)

---

## 14. Consequences

### Positive

- **Reliability by topology, not discipline.** Constraints and verifiers execute because the graph makes them non-skippable, not because a developer remembered to add them.
- **Self-correcting agents.** The retry loop with issue injection means agents improve their output within a single invocation, without human intervention.
- **Observable quality.** Constraint pass rates, verification rates, and retry counts become standard metrics across all agents.
- **Consistent developer experience.** Every agent follows the same pattern: implement `_build()`, declare hooks. No bespoke graph wiring.
- **Backwards compatible (modulo `_build()` return type).** Agents that only implement `_build()` with no harness hooks compile identically to today.

### Negative / Trade-offs

- **Breaking change to `_build()`.** The return type changes from `CompiledStateGraph` to `StateGraph`. This requires a one-line change per agent (`grep -r "graph.compile()" agents/`) and is low-risk at our current agent count, but it is a breaking change.
- **Added latency per invocation.** Constraint nodes are fast (milliseconds). LLM verifiers add a full LLM call. Retries multiply this. Mitigation: latency budgets in ADR-002 eval assertions, and agents can opt for deterministic-only verification when latency is critical.
- **`weave_harness()` complexity.** The wiring function that inserts nodes into a mutable graph is non-trivial. Accepted trade-off: complexity lives once in the framework, not distributed across every agent. It must be thoroughly tested.
- **Constraint authoring effort.** Each agent needs domain-specific constraints. This is intentional: the harness engineering ethos is to engineer a solution for every observed failure mode. Over time, common constraints (`TenantIsolation`, `SchemaFieldExistence`) become reusable library components.

### Open Questions

1. **Supervisor-level harness.** Task decomposition (Pattern 1) and session handoffs (Pattern 2) need a separate design. Should the Supervisor use a distinct `SupervisorBuilder` or reuse `AgentBuilder` hooks for its sub-steps?
2. **Constraint hot-reload.** Should constraints be loadable from XMS (like prompts), allowing runtime updates without redeployment? Powerful but adds resolution complexity.
3. **Verification cost control.** LLM verifiers use tokens. Should the framework enforce a token budget per invocation, or leave cost control to latency-budget assertions in evals?
4. **Worker node discovery.** The current design uses `metadata={"role": "worker"}` tagging. Should we instead use a naming convention, or require agents to explicitly declare the worker node name via a hook?

---

## References

- OpenAI, "Harness engineering: leveraging Codex in an agent-first world" (2026)
- Anthropic, "Effective harnesses for long-running agents" (2025)
- LangChain, "Improving Deep Agents with Harness Engineering" (2026)
- Hugo Bowne-Anderson / Jeff Huber (Chroma), "Harness Engineering: Why Agent Context Isn't Enough" (2026)
- ActBI Agent Architecture (internal, Dec 2025)
- ADR-002: Evaluation Framework Design (internal, Jan 2026)
- ADR-003: Observability & Feature Flag Strategy (internal, Mar 2026)
