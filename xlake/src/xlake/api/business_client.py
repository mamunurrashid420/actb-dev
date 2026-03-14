"""BusinessClient for the XLake Unified API.

The BusinessClient is the semantic and knowledge layer of XLake. It owns
everything related to business meaning, domain knowledge, schema semantics,
KPI definitions, relationships, and conversational knowledge.

Backed by:
- CustomerContextStore (schema, facts, semantic)
- CustomerAppLogicStore (conversation, KPI storage)
- CoreContextStore (KnowledgeNuggets, BusinessMetrics, IndustryTerms)
- CoreExternalSourceStore (semantic search)

Five sub-clients:
- KPIBusinessClient: Define and retrieve KPI/metric definitions
- SchemaBusinessClient: Manage schema semantics and relationships
- FactsBusinessClient: Store and retrieve business facts
- SemanticBusinessClient: Semantic search and graph operations
- ConversationBusinessClient: Conversation context and state
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..core import TenantContext, UserContext
from .models import (
    KPI,
    ActiveState,
    ConversationContext,
    Entity,
    FactCreate,
    FactInfo,
    FullSchema,
    GraphNeighbor,
    GraphResult,
    IndustryTermCreate,
    IndustryTermInfo,
    IndustryTermSummary,
    InsightInput,
    KnowledgeNuggetCreate,
    KnowledgeNuggetInfo,
    KnowledgeNuggetSummary,
    KnowledgeObject,
    KPIDefinition,
    KPISummary,
    Relationship,
    SchemaSemantics,
    StateUpdate,
)

if TYPE_CHECKING:
    from ..stores import (
        CoreContextStore,
        CoreExternalSourceStore,
        CustomerAppLogicStore,
        CustomerContextStore,
    )


# =============================================================================
# KPIBusinessClient
# =============================================================================


class KPIBusinessClient:
    """Sub-client for KPI/metric operations.

    Accessed via `business.kpi`.

    Backed by CoreContextStore (BusinessMetrics) and CustomerAppLogicStore.
    """

    def __init__(
        self,
        core_context_store: CoreContextStore,
        app_logic_store: CustomerAppLogicStore,
    ) -> None:
        """Initialize the KPI sub-client.

        Args:
            core_context_store: CoreContextStore for global metric definitions.
            app_logic_store: CustomerAppLogicStore for customer-specific KPIs.
        """
        self._core_context = core_context_store
        self._app_logic = app_logic_store

    def list(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KPISummary]:
        """List all KPIs available to the user.

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of KPI summaries.
        """
        # Search for all business metrics (core metrics)
        metrics = self._core_context.search_business_metrics(
            "", tenant=tenant, user=user
        )
        return [
            KPISummary(
                kpi_id=m.metric_id,
                name=m.name,
                domain=m.domain,
                description=m.description,
                output_unit=m.output_unit,
            )
            for m in metrics
        ]

    def get(
        self,
        kpi_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KPI:
        """Get a KPI by ID.

        Args:
            kpi_id: Identifier of the KPI.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Full KPI information.

        Raises:
            KeyError: If the KPI is not found.
        """
        metric = self._core_context.get_business_metric(
            kpi_id, tenant=tenant, user=user
        )
        return KPI(
            kpi_id=metric.metric_id,
            name=metric.name,
            domain=metric.domain,
            description=metric.description,
            formula=metric.formula,
            formula_type=metric.formula_type,
            input_fields=metric.input_fields,
            output_unit=metric.output_unit,
            tags=metric.tags,
            created_at=metric.created_at,
            updated_at=metric.updated_at,
        )

    def get_definition(
        self,
        kpi_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KPIDefinition:
        """Get the full definition of a KPI including formula and lineage.

        Args:
            kpi_id: Identifier of the KPI.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            KPI definition with formula and lineage.

        Raises:
            KeyError: If the KPI is not found.
        """
        metric = self._core_context.get_business_metric(
            kpi_id, tenant=tenant, user=user
        )
        # Convert lineage to dict format if it's a list
        lineage_dict = (
            metric.lineage
            if isinstance(metric.lineage, dict)
            else {
                "sources": metric.lineage if metric.lineage else [],
            }
        )
        return KPIDefinition(
            kpi_id=metric.metric_id,
            name=metric.name,
            domain=metric.domain,
            description=metric.description,
            formula=metric.formula,
            formula_type=metric.formula_type,
            input_fields=metric.input_fields,
            output_unit=metric.output_unit,
            lineage=lineage_dict,
            examples=[],  # Could be populated from reference_uris
        )

    def add(
        self,
        kpi: KPI,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add a new KPI definition.

        Args:
            kpi: KPI information to add.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created KPI.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        from ..models import BusinessMetric

        metric = BusinessMetric(
            metric_id=kpi.kpi_id or "",
            name=kpi.name,
            domain=kpi.domain,
            description=kpi.description,
            formula=kpi.formula,
            formula_type=kpi.formula_type,
            input_fields=kpi.input_fields,
            output_unit=kpi.output_unit,
            tags=kpi.tags,
            created_at=kpi.created_at or datetime.now(),
            updated_at=kpi.updated_at or datetime.now(),
        )
        return self._core_context.upsert_business_metric(
            metric, tenant=tenant, user=user
        )

    def update(
        self,
        kpi_id: str,
        updates: KPI,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KPI:
        """Update an existing KPI.

        Args:
            kpi_id: Identifier of the KPI to update.
            updates: KPI information with updated fields.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated KPI.

        Raises:
            KeyError: If the KPI is not found.
            PermissionError: If the user lacks write permissions.
        """
        from ..models import BusinessMetric

        # Get existing to preserve unchanged fields
        existing = self._core_context.get_business_metric(
            kpi_id, tenant=tenant, user=user
        )

        metric = BusinessMetric(
            metric_id=kpi_id,
            name=updates.name or existing.name,
            domain=updates.domain or existing.domain,
            description=updates.description or existing.description,
            formula=updates.formula
            if updates.formula is not None
            else existing.formula,
            formula_type=updates.formula_type or existing.formula_type,
            input_fields=updates.input_fields or existing.input_fields,
            output_unit=updates.output_unit
            if updates.output_unit is not None
            else existing.output_unit,
            tags=updates.tags or existing.tags,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )
        self._core_context.upsert_business_metric(metric, tenant=tenant, user=user)
        return self.get(kpi_id, tenant=tenant, user=user)

    def delete(
        self,
        kpi_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a KPI.

        Args:
            kpi_id: Identifier of the KPI to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the KPI is not found.
            PermissionError: If the user lacks delete permissions.
        """
        self._core_context.delete_business_metric(kpi_id, tenant=tenant, user=user)


# =============================================================================
# SchemaBusinessClient
# =============================================================================


class SchemaBusinessClient:
    """Sub-client for schema semantic operations.

    Accessed via `business.schema`.

    Backed by CustomerContextStore.
    """

    def __init__(self, context_store: CustomerContextStore) -> None:
        """Initialize the schema sub-client.

        Args:
            context_store: CustomerContextStore for schema management.
        """
        self._context_store = context_store

    def get(
        self,
        schema_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> SchemaSemantics:
        """Get semantic information about a schema.

        Args:
            schema_id: Identifier of the schema.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Schema semantics including version and entity count.

        Raises:
            KeyError: If the schema is not found.
        """
        record = self._context_store.get_schema_context(
            schema_id, tenant=tenant, user=user
        )
        schema_data = record.data_schema
        return SchemaSemantics(
            schema_id=schema_data.get("schema_id", schema_id),
            name=schema_data.get("name", ""),
            version=schema_data.get("version", 1),
            description=schema_data.get("description"),
            entity_count=len(record.facts_by_entity),
        )

    def get_full(
        self,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[FullSchema]:
        """Get the complete schema with all entities (restricted by permissions).

        Args:
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of full schemas with all entities and facts.
        """
        # Search for all schemas
        records = self._context_store.search_context(
            "", top_k_schemas=100, tenant=tenant, user=user
        )
        result = []
        for record in records:
            schema_data = record.data_schema
            facts_dict: dict[str, list[dict[str, Any]]] = {}
            for entity_id, facts in record.facts_by_entity.items():
                facts_dict[entity_id] = [
                    {
                        "fact_id": f.fact_id,
                        "text": f.text,
                        "date": f.date.isoformat() if f.date else None,
                        "source": f.source,
                        "tags": f.tags,
                    }
                    for f in facts
                ]
            result.append(
                FullSchema(
                    schema_id=schema_data.get("schema_id", ""),
                    name=schema_data.get("name", ""),
                    version=schema_data.get("version", 1),
                    description=schema_data.get("description"),
                    databases=schema_data.get("databases", []),
                    facts_by_entity=facts_dict,
                )
            )
        return result

    def add_relationship(
        self,
        field_a: str,
        field_b: str,
        metadata: dict[str, Any],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add a relationship between two fields/tables.

        Args:
            field_a: Identifier of the first field/table.
            field_b: Identifier of the second field/table.
            metadata: Relationship metadata (type, description, etc.).
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created relationship.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        # Store the relationship as a fact on field_a
        relationship_type = metadata.get("type", "related_to")
        text = f"{relationship_type}: {field_b}"
        if "description" in metadata:
            text += f" - {metadata['description']}"

        # Extract schema_id from field_a (format: schema_id:entity_id or just use first schema)
        schema_id = metadata.get("schema_id", "")
        if not schema_id:
            # Try to find schema from search
            records = self._context_store.search_context(
                field_a, top_k_schemas=1, tenant=tenant, user=user
            )
            if records:
                schema_id = records[0].data_schema.get("schema_id", "")

        if not schema_id:
            raise ValueError(
                "schema_id must be provided in metadata or derivable from field_a"
            )

        result = self._context_store.add_fact(
            schema_id=schema_id,
            entity_id=field_a,
            text=text,
            source="relationship",
            tags=[relationship_type, "relationship"],
            tenant=tenant,
            user=user,
        )
        return result.get("fact_id", "")

    def add_field_metadata(
        self,
        field_id: str,
        metadata: dict[str, Any],
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add metadata/explanation to a field.

        Args:
            field_id: Identifier of the field.
            metadata: Metadata to add (description, units, etc.).
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created fact.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        schema_id = metadata.get("schema_id", "")
        if not schema_id:
            records = self._context_store.search_context(
                field_id, top_k_schemas=1, tenant=tenant, user=user
            )
            if records:
                schema_id = records[0].data_schema.get("schema_id", "")

        if not schema_id:
            raise ValueError("schema_id must be provided in metadata")

        text = metadata.get("description", metadata.get("text", ""))
        if not text:
            # Build text from other metadata fields
            parts = []
            if "units" in metadata:
                parts.append(f"Units: {metadata['units']}")
            if "data_type" in metadata:
                parts.append(f"Type: {metadata['data_type']}")
            text = ". ".join(parts) if parts else "No description provided"

        result = self._context_store.add_fact(
            schema_id=schema_id,
            entity_id=field_id,
            text=text,
            source=metadata.get("source", "user_input"),
            tags=metadata.get("tags", ["metadata"]),
            tenant=tenant,
            user=user,
        )
        return result.get("fact_id", "")

    def get_entity(
        self,
        entity_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> Entity:
        """Get an entity by ID with its metadata and relationships.

        Args:
            entity_id: Identifier of the entity.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Entity with metadata and relationships.

        Raises:
            KeyError: If the entity is not found.
        """
        # Search for the entity
        records = self._context_store.search_context(
            entity_id, top_k_schemas=1, facts_per_entity=50, tenant=tenant, user=user
        )
        if not records:
            raise KeyError(f"Entity not found: {entity_id}")

        record = records[0]
        facts = record.facts_by_entity.get(entity_id, [])

        # Build relationships from facts tagged as relationships
        relationships = []
        for fact in facts:
            if "relationship" in (fact.tags or []):
                # Parse relationship from fact text
                parts = fact.text.split(":", 1)
                if len(parts) == 2:
                    rel_type = parts[0].strip()
                    target = parts[1].strip().split(" - ")[0].strip()
                    relationships.append(
                        Relationship(
                            target_id=target,
                            target_type="field",
                            relationship_type=rel_type,
                            confidence=1.0,
                        )
                    )

        return Entity(
            entity_id=entity_id,
            entity_type="field",
            name=entity_id.split(".")[-1] if "." in entity_id else entity_id,
            description=facts[0].text if facts else None,
            relationships=relationships,
            tenant_id=tenant.identity.tenant_id,
        )


# =============================================================================
# FactsBusinessClient
# =============================================================================


class FactsBusinessClient:
    """Sub-client for business fact operations.

    Accessed via `business.facts`.

    Backed by CustomerContextStore and CoreContextStore.
    """

    def __init__(
        self,
        context_store: CustomerContextStore,
        core_context_store: CoreContextStore,
    ) -> None:
        """Initialize the facts sub-client.

        Args:
            context_store: CustomerContextStore for customer facts.
            core_context_store: CoreContextStore for core knowledge.
        """
        self._context_store = context_store
        self._core_context = core_context_store

    def add(
        self,
        entity_id: str,
        fact: FactCreate,
        *,
        schema_id: str,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add a fact to an entity.

        Args:
            entity_id: Identifier of the entity.
            fact: Fact information to add.
            schema_id: Identifier of the schema containing the entity.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created fact.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        result = self._context_store.add_fact(
            schema_id=schema_id,
            entity_id=entity_id,
            text=fact.text,
            date=fact.date.isoformat() if fact.date else None,
            source=fact.source,
            tags=fact.tags,
            tenant=tenant,
            user=user,
        )
        return result.get("fact_id", "")

    def list(
        self,
        entity_id: str,
        *,
        schema_id: str,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[FactInfo]:
        """List facts for an entity.

        Args:
            entity_id: Identifier of the entity.
            schema_id: Identifier of the schema containing the entity.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of facts for the entity.
        """
        facts_dict = self._context_store.get_entity_facts(
            schema_id=schema_id,
            entity_ids=[entity_id],
            tenant=tenant,
            user=user,
        )
        facts = facts_dict.get(entity_id, [])
        return [
            FactInfo(
                fact_id=f.fact_id,
                entity_id=f.entity_id,
                text=f.text,
                date=f.date,
                source=f.source,
                tags=f.tags or [],
            )
            for f in facts
        ]

    def get(
        self,
        fact_id: str,
        *,
        schema_id: str,
        tenant: TenantContext,
        user: UserContext,
    ) -> FactInfo:
        """Get a specific fact by ID.

        Args:
            fact_id: Identifier of the fact.
            schema_id: Identifier of the schema containing the fact.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Fact information.

        Raises:
            KeyError: If the fact is not found.
        """
        # Search across all entities for this fact
        record = self._context_store.get_schema_context(
            schema_id, tenant=tenant, user=user
        )
        for _entity_id, facts in record.facts_by_entity.items():
            for f in facts:
                if f.fact_id == fact_id:
                    return FactInfo(
                        fact_id=f.fact_id,
                        entity_id=f.entity_id,
                        text=f.text,
                        date=f.date,
                        source=f.source,
                        tags=f.tags or [],
                    )
        raise KeyError(f"Fact not found: {fact_id}")

    def update(
        self,
        fact_id: str,
        updates: FactCreate,
        *,
        schema_id: str,
        tenant: TenantContext,
        user: UserContext,
    ) -> FactInfo:
        """Update a fact.

        Args:
            fact_id: Identifier of the fact to update.
            updates: Updated fact information.
            schema_id: Identifier of the schema containing the fact.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated fact information.

        Raises:
            KeyError: If the fact is not found.
            PermissionError: If the user lacks write permissions.
        """
        self._context_store.modify_fact(
            schema_id=schema_id,
            fact_id=fact_id,
            text=updates.text,
            date=updates.date.isoformat() if updates.date else None,
            source=updates.source,
            tags=updates.tags,
            tenant=tenant,
            user=user,
        )
        return self.get(fact_id, schema_id=schema_id, tenant=tenant, user=user)

    def delete(
        self,
        fact_id: str,
        *,
        schema_id: str,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a fact.

        Args:
            fact_id: Identifier of the fact to delete.
            schema_id: Identifier of the schema containing the fact.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the fact is not found.
            PermissionError: If the user lacks delete permissions.
        """
        self._context_store.delete_fact(
            schema_id=schema_id,
            fact_id=fact_id,
            tenant=tenant,
            user=user,
        )


# =============================================================================
# SemanticBusinessClient
# =============================================================================


class SemanticBusinessClient:
    """Sub-client for semantic search and graph operations.

    Accessed via `business.semantic`.

    Backed by CustomerContextStore and CoreExternalSourceStore.
    """

    def __init__(
        self,
        context_store: CustomerContextStore,
        core_context_store: CoreContextStore,
        external_store: CoreExternalSourceStore | None = None,
    ) -> None:
        """Initialize the semantic sub-client.

        Args:
            context_store: CustomerContextStore for customer semantics.
            core_context_store: CoreContextStore for core knowledge.
            external_store: Optional CoreExternalSourceStore for external signals.
        """
        self._context_store = context_store
        self._core_context = core_context_store
        self._external_store = external_store

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        top_k: int = 10,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[Entity]:
        """Semantic search across fields, tables, KPIs, concepts, and metadata.

        Args:
            query: Natural language search query.
            filters: Optional filters (entity_type, domain, etc.).
            top_k: Maximum number of results to return.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of matching entities.
        """
        results: list[Entity] = []

        # Search customer context (schemas and facts)
        records = self._context_store.search_context(
            query,
            top_k_schemas=min(top_k, 5),
            facts_per_entity=10,
            tenant=tenant,
            user=user,
        )
        for record in records:
            schema_id = record.data_schema.get("schema_id", "")
            for entity_id, facts in record.facts_by_entity.items():
                if len(results) >= top_k:
                    break
                results.append(
                    Entity(
                        entity_id=entity_id,
                        entity_type="field",
                        name=entity_id.split(".")[-1]
                        if "." in entity_id
                        else entity_id,
                        description=facts[0].text if facts else None,
                        metadata={"schema_id": schema_id},
                        tenant_id=tenant.identity.tenant_id,
                    )
                )

        # Search core business metrics
        if len(results) < top_k:
            metrics = self._core_context.search_business_metrics(
                query, top_k=top_k - len(results), tenant=tenant, user=user
            )
            for m in metrics:
                results.append(
                    Entity(
                        entity_id=m.metric_id,
                        entity_type="kpi",
                        name=m.name,
                        description=m.description,
                        metadata={"domain": m.domain, "formula": m.formula},
                    )
                )

        # Search core knowledge nuggets
        if len(results) < top_k:
            nuggets = self._core_context.search_knowledge_nuggets(
                query, top_k=top_k - len(results), tenant=tenant, user=user
            )
            for n in nuggets:
                results.append(
                    Entity(
                        entity_id=n.nugget_id,
                        entity_type="concept",
                        name=n.category,
                        description=n.content,
                        metadata={"domain": n.domain},
                    )
                )

        return results[:top_k]

    def graph(
        self,
        entity_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> GraphResult:
        """Get the semantic graph surrounding an entity.

        This is the core semantic operation that returns structured + semantic
        neighbors of an entity for agent reasoning.

        Args:
            entity_id: Identifier of the entity.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            GraphResult with entity and its neighbors.
        """
        # Search for the entity and related items
        records = self._context_store.search_context(
            entity_id,
            top_k_schemas=3,
            facts_per_entity=50,
            tenant=tenant,
            user=user,
        )

        # Build the central entity
        entity_name = entity_id.split(".")[-1] if "." in entity_id else entity_id
        entity = Entity(
            entity_id=entity_id,
            entity_type="field",
            name=entity_name,
            tenant_id=tenant.identity.tenant_id,
        )

        neighbors: list[GraphNeighbor] = []

        # Add neighbors from schema relationships
        for record in records:
            schema_id = record.data_schema.get("schema_id", "")
            schema_name = record.data_schema.get("name", "")

            # Add schema as a neighbor
            if schema_id:
                neighbors.append(
                    GraphNeighbor(
                        id=schema_id,
                        type="table",
                        name=schema_name,
                        relationship="belongs_to_schema",
                        source="structured",
                        confidence=1.0,
                    )
                )

            # Add facts as metadata sentence neighbors
            facts = record.facts_by_entity.get(entity_id, [])
            for fact in facts[:10]:  # Limit to 10 facts
                neighbors.append(
                    GraphNeighbor(
                        id=fact.fact_id,
                        type="metadata_sentence",
                        relationship="explained_by",
                        source="document_metadata",
                        text=fact.text,
                        confidence=0.9,
                    )
                )

        # Search for related KPIs
        kpis = self._core_context.search_business_metrics(
            entity_name, top_k=5, tenant=tenant, user=user
        )
        for kpi in kpis:
            if entity_id in kpi.input_fields or entity_name.lower() in kpi.name.lower():
                neighbors.append(
                    GraphNeighbor(
                        id=kpi.metric_id,
                        type="kpi",
                        name=kpi.name,
                        relationship="used_in_kpi",
                        source="structured",
                        confidence=1.0,
                    )
                )

        # Search for related external signals if available
        if self._external_store:
            try:
                signals = self._external_store.search_metadata(
                    entity_name, top_k=3, tenant=tenant, user=user
                )
                for signal in signals:
                    neighbors.append(
                        GraphNeighbor(
                            id=signal.dataset_id,
                            type="external_signal",
                            name=signal.name,
                            relationship="contextual_influence",
                            source="semantic",
                            confidence=signal.score,
                        )
                    )
            except Exception:
                pass  # External store may not be available

        return GraphResult(entity=entity, neighbors=neighbors)

    def add_knowledge(
        self,
        knowledge: KnowledgeObject,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add new knowledge to the semantic store.

        Args:
            knowledge: Knowledge object to add.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created knowledge entry.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        # Determine where to store based on knowledge type
        if knowledge.knowledge_type in ("explanation", "metadata"):
            # Store as a fact in CustomerContextStore
            if not knowledge.entity_id:
                raise ValueError(
                    "entity_id is required for explanation/metadata knowledge"
                )

            # Find the schema for this entity
            records = self._context_store.search_context(
                knowledge.entity_id, top_k_schemas=1, tenant=tenant, user=user
            )
            if not records:
                raise ValueError(
                    f"Could not find schema for entity: {knowledge.entity_id}"
                )

            schema_id = records[0].data_schema.get("schema_id", "")
            result = self._context_store.add_fact(
                schema_id=schema_id,
                entity_id=knowledge.entity_id,
                text=knowledge.content,
                source=knowledge.source,
                tags=[knowledge.knowledge_type] + knowledge.tags,
                tenant=tenant,
                user=user,
            )
            return result.get("fact_id", "")

        elif knowledge.knowledge_type == "definition":
            # Store as a knowledge nugget in CoreContextStore
            from ..models import KnowledgeNugget

            nugget = KnowledgeNugget(
                nugget_id="",
                domain=knowledge.tags[0] if knowledge.tags else "general",
                category=knowledge.knowledge_type,
                content=knowledge.content,
                tags=knowledge.tags,
                sources=[knowledge.source] if knowledge.source else [],
                confidence=knowledge.confidence,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            return self._core_context.upsert_knowledge_nugget(
                nugget, tenant=tenant, user=user
            )

        else:
            # For relationships and corrections, store as facts
            if not knowledge.entity_id:
                raise ValueError("entity_id is required")

            records = self._context_store.search_context(
                knowledge.entity_id, top_k_schemas=1, tenant=tenant, user=user
            )
            if not records:
                raise ValueError(
                    f"Could not find schema for entity: {knowledge.entity_id}"
                )

            schema_id = records[0].data_schema.get("schema_id", "")
            result = self._context_store.add_fact(
                schema_id=schema_id,
                entity_id=knowledge.entity_id,
                text=knowledge.content,
                source=knowledge.source,
                tags=[knowledge.knowledge_type] + knowledge.tags,
                tenant=tenant,
                user=user,
            )
            return result.get("fact_id", "")


# =============================================================================
# ConversationBusinessClient
# =============================================================================


class ConversationBusinessClient:
    """Sub-client for conversation context and state operations.

    Accessed via `business.conversation`.

    Backed by CustomerAppLogicStore.
    """

    def __init__(self, app_logic_store: CustomerAppLogicStore) -> None:
        """Initialize the conversation sub-client.

        Args:
            app_logic_store: CustomerAppLogicStore for conversation data.
        """
        self._app_logic = app_logic_store

    def get_context(
        self,
        thread_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ConversationContext:
        """Get the context for a conversation thread.

        Args:
            thread_id: Identifier of the conversation thread.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Conversation context with summary and entities.

        Raises:
            KeyError: If the conversation is not found.
        """
        conversation = self._app_logic.get_conversation(thread_id)
        messages = conversation.get("messages", [])

        # Extract mentioned entities from messages
        mentioned_entities: list[str] = []
        recent_queries: list[str] = []
        insights: list[str] = []

        for msg in messages[-10:]:  # Last 10 messages
            text = msg.get("text", "")
            if msg.get("sender") == "user":
                recent_queries.append(text)
            # Extract entity mentions (simplified)
            mentioned_entities.extend(msg.get("mentioned_entities", []))
            # Extract insights
            if msg.get("type") == "insight":
                insights.append(text)

        return ConversationContext(
            thread_id=thread_id,
            summary=conversation.get("summary"),
            mentioned_entities=list(set(mentioned_entities)),
            recent_queries=recent_queries[-5:],
            insights=insights,
        )

    def get_active_state(
        self,
        thread_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> ActiveState:
        """Get the active state for a conversation thread.

        Args:
            thread_id: Identifier of the conversation thread.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Active state including charts, filters, and simulations.

        Raises:
            KeyError: If the conversation is not found.
        """
        conversation = self._app_logic.get_conversation(thread_id)
        state = conversation.get("active_state", {})

        return ActiveState(
            thread_id=thread_id,
            active_chart_id=state.get("active_chart_id"),
            active_stack_id=state.get("active_stack_id"),
            active_dashboard_id=state.get("active_dashboard_id"),
            active_simulations=state.get("active_simulations", []),
            active_filters=state.get("active_filters", []),
            last_referenced_entities=state.get("last_referenced_entities", []),
        )

    def add_insight(
        self,
        thread_id: str,
        insight: InsightInput,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add an insight to a conversation.

        Args:
            thread_id: Identifier of the conversation thread.
            insight: Insight to add.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the added insight.

        Raises:
            KeyError: If the conversation is not found.
        """
        import uuid

        insight_id = str(uuid.uuid4())
        message = {
            "id": insight_id,
            "type": "insight",
            "sender": "assistant",
            "text": insight.summary,
            "detail": insight.detail,
            "related_entities": insight.related_entities,
            "related_charts": insight.related_charts,
            "confidence": insight.confidence,
        }
        self._app_logic.append_message(thread_id, message)
        return insight_id

    def update_state(
        self,
        thread_id: str,
        state: StateUpdate,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Update the active state for a conversation.

        Args:
            thread_id: Identifier of the conversation thread.
            state: State updates to apply.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the conversation is not found.
        """
        # Get existing conversation
        conversation = self._app_logic.get_conversation(thread_id)
        existing_state = conversation.get("active_state", {})

        # Apply updates (only non-None values)
        if state.active_chart_id is not None:
            existing_state["active_chart_id"] = state.active_chart_id
        if state.active_stack_id is not None:
            existing_state["active_stack_id"] = state.active_stack_id
        if state.active_dashboard_id is not None:
            existing_state["active_dashboard_id"] = state.active_dashboard_id
        if state.active_simulations is not None:
            existing_state["active_simulations"] = state.active_simulations
        if state.active_filters is not None:
            existing_state["active_filters"] = state.active_filters
        if state.last_referenced_entities is not None:
            existing_state["last_referenced_entities"] = state.last_referenced_entities
        if state.summary is not None:
            conversation["summary"] = state.summary

        # Store state update as a system message
        self._app_logic.append_message(
            thread_id,
            {
                "type": "state_update",
                "sender": "system",
                "active_state": existing_state,
            },
        )


# =============================================================================
# KnowledgeBusinessClient
# =============================================================================


class KnowledgeBusinessClient:
    """Sub-client for knowledge nugget operations.

    Accessed via `business.knowledge`.

    Backed by CoreContextStore (KnowledgeNuggets).
    """

    def __init__(self, core_context_store: CoreContextStore) -> None:
        """Initialize the knowledge sub-client.

        Args:
            core_context_store: CoreContextStore for knowledge nuggets.
        """
        self._core_context = core_context_store

    def search(
        self,
        query: str,
        *,
        domains: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KnowledgeNuggetSummary]:
        """Search for knowledge nuggets by semantic similarity.

        Args:
            query: Natural language search query.
            domains: Optional list of domains to filter by.
            top_k: Maximum number of results to return.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of matching knowledge nugget summaries.
        """
        nuggets = self._core_context.search_knowledge_nuggets(
            query, domains=domains, top_k=top_k, tenant=tenant, user=user
        )
        return [
            KnowledgeNuggetSummary(
                nugget_id=n.nugget_id,
                domain=n.domain,
                category=n.category,
                content=n.content,
                confidence=n.confidence,
            )
            for n in nuggets
        ]

    def list_by_domain(
        self,
        domain: str,
        *,
        category: str | None = None,
        limit: int = 50,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[KnowledgeNuggetSummary]:
        """List knowledge nuggets filtered by domain and optionally category.

        Args:
            domain: Domain to filter by (e.g., "finance", "supply_chain").
            category: Optional sub-category within domain.
            limit: Maximum number of results to return.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of knowledge nugget summaries.
        """
        nuggets = self._core_context.get_knowledge_nuggets_by_domain(
            domain, category=category, limit=limit, tenant=tenant, user=user
        )
        return [
            KnowledgeNuggetSummary(
                nugget_id=n.nugget_id,
                domain=n.domain,
                category=n.category,
                content=n.content,
                confidence=n.confidence,
            )
            for n in nuggets
        ]

    def get(
        self,
        nugget_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KnowledgeNuggetInfo:
        """Get a knowledge nugget by ID.

        Args:
            nugget_id: Identifier of the knowledge nugget.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Full knowledge nugget information.

        Raises:
            KeyError: If the nugget is not found.
        """
        nugget = self._core_context.get_knowledge_nugget(
            nugget_id, tenant=tenant, user=user
        )
        return KnowledgeNuggetInfo(
            nugget_id=nugget.nugget_id,
            domain=nugget.domain,
            category=nugget.category,
            content=nugget.content,
            tags=nugget.tags,
            sources=nugget.sources,
            reference_uris=nugget.reference_uris,
            confidence=nugget.confidence,
            created_at=nugget.created_at,
            updated_at=nugget.updated_at,
        )

    def add(
        self,
        nugget: KnowledgeNuggetCreate,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add a new knowledge nugget.

        Args:
            nugget: Knowledge nugget information to add.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created nugget.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        from ..models import KnowledgeNugget

        store_nugget = KnowledgeNugget(
            nugget_id="",
            domain=nugget.domain,
            category=nugget.category,
            content=nugget.content,
            tags=nugget.tags or [],
            sources=nugget.sources or [],
            reference_uris=nugget.reference_uris or [],
            confidence=nugget.confidence,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return self._core_context.upsert_knowledge_nugget(
            store_nugget, tenant=tenant, user=user
        )

    def update(
        self,
        nugget_id: str,
        updates: KnowledgeNuggetCreate,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> KnowledgeNuggetInfo:
        """Update an existing knowledge nugget.

        Args:
            nugget_id: Identifier of the nugget to update.
            updates: Updated nugget information.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated knowledge nugget information.

        Raises:
            KeyError: If the nugget is not found.
            PermissionError: If the user lacks write permissions.
        """
        from ..models import KnowledgeNugget

        # Get existing to preserve timestamps
        existing = self._core_context.get_knowledge_nugget(
            nugget_id, tenant=tenant, user=user
        )

        store_nugget = KnowledgeNugget(
            nugget_id=nugget_id,
            domain=updates.domain,
            category=updates.category,
            content=updates.content,
            tags=updates.tags or existing.tags,
            sources=updates.sources or existing.sources,
            reference_uris=updates.reference_uris or existing.reference_uris,
            confidence=updates.confidence,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )
        self._core_context.upsert_knowledge_nugget(
            store_nugget, tenant=tenant, user=user
        )
        return self.get(nugget_id, tenant=tenant, user=user)

    def delete(
        self,
        nugget_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete a knowledge nugget.

        Args:
            nugget_id: Identifier of the nugget to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the nugget is not found.
            PermissionError: If the user lacks delete permissions.
        """
        self._core_context.delete_knowledge_nugget(nugget_id, tenant=tenant, user=user)


# =============================================================================
# IndustryBusinessClient
# =============================================================================


class IndustryBusinessClient:
    """Sub-client for industry term operations.

    Accessed via `business.industry`.

    Backed by CoreContextStore (IndustryTerms).
    """

    def __init__(self, core_context_store: CoreContextStore) -> None:
        """Initialize the industry sub-client.

        Args:
            core_context_store: CoreContextStore for industry terms.
        """
        self._core_context = core_context_store

    def search(
        self,
        query: str,
        *,
        industries: list[str] | None = None,
        top_k: int = 10,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[IndustryTermSummary]:
        """Search for industry terms by semantic similarity.

        Args:
            query: Natural language search query.
            industries: Optional list of industries to filter by.
            top_k: Maximum number of results to return.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of matching industry term summaries.
        """
        terms = self._core_context.search_industry_terms(
            query, industries=industries, top_k=top_k, tenant=tenant, user=user
        )
        return [
            IndustryTermSummary(
                term_id=t.term_id,
                term=t.term,
                industry=t.industry,
                definition=t.definition,
            )
            for t in terms
        ]

    def get(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTermInfo:
        """Get an industry term by ID.

        Args:
            term_id: Identifier of the industry term.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Full industry term information.

        Raises:
            KeyError: If the term is not found.
        """
        term = self._core_context.get_industry_term(term_id, tenant=tenant, user=user)
        return IndustryTermInfo(
            term_id=term.term_id,
            term=term.term,
            definition=term.definition,
            industry=term.industry,
            synonyms=term.synonyms,
            related_terms=term.related_terms,
            antonyms=term.antonyms,
            examples=term.examples,
            tags=term.tags,
            reference_uris=term.reference_uris,
            created_at=term.created_at,
            updated_at=term.updated_at,
        )

    def get_by_name(
        self,
        term: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTermInfo | None:
        """Get an industry term by its name.

        Args:
            term: The term name to look up.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Industry term information, or None if not found.
        """
        result = self._core_context.get_industry_term_by_name(
            term, tenant=tenant, user=user
        )
        if result is None:
            return None
        return IndustryTermInfo(
            term_id=result.term_id,
            term=result.term,
            definition=result.definition,
            industry=result.industry,
            synonyms=result.synonyms,
            related_terms=result.related_terms,
            antonyms=result.antonyms,
            examples=result.examples,
            tags=result.tags,
            reference_uris=result.reference_uris,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    def get_related(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> list[IndustryTermInfo]:
        """Get all related industry terms for a given term.

        Args:
            term_id: Identifier of the term to get relations for.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            List of related industry terms.

        Raises:
            KeyError: If the term is not found.
        """
        terms = self._core_context.get_related_industry_terms(
            term_id, tenant=tenant, user=user
        )
        return [
            IndustryTermInfo(
                term_id=t.term_id,
                term=t.term,
                definition=t.definition,
                industry=t.industry,
                synonyms=t.synonyms,
                related_terms=t.related_terms,
                antonyms=t.antonyms,
                examples=t.examples,
                tags=t.tags,
                reference_uris=t.reference_uris,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in terms
        ]

    def add(
        self,
        term: IndustryTermCreate,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> str:
        """Add a new industry term.

        Args:
            term: Industry term information to add.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Identifier of the created term.

        Raises:
            PermissionError: If the user lacks write permissions.
        """
        from ..models import IndustryTerm

        store_term = IndustryTerm(
            term_id="",
            term=term.term,
            definition=term.definition,
            industry=term.industry,
            synonyms=term.synonyms or [],
            related_terms=term.related_terms or [],
            antonyms=term.antonyms or [],
            examples=term.examples or [],
            tags=term.tags or [],
            reference_uris=term.reference_uris or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return self._core_context.upsert_industry_term(
            store_term, tenant=tenant, user=user
        )

    def update(
        self,
        term_id: str,
        updates: IndustryTermCreate,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> IndustryTermInfo:
        """Update an existing industry term.

        Args:
            term_id: Identifier of the term to update.
            updates: Updated term information.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Returns:
            Updated industry term information.

        Raises:
            KeyError: If the term is not found.
            PermissionError: If the user lacks write permissions.
        """
        from ..models import IndustryTerm

        # Get existing to preserve timestamps
        existing = self._core_context.get_industry_term(
            term_id, tenant=tenant, user=user
        )

        store_term = IndustryTerm(
            term_id=term_id,
            term=updates.term,
            definition=updates.definition,
            industry=updates.industry,
            synonyms=updates.synonyms or existing.synonyms,
            related_terms=updates.related_terms or existing.related_terms,
            antonyms=updates.antonyms or existing.antonyms,
            examples=updates.examples or existing.examples,
            tags=updates.tags or existing.tags,
            reference_uris=updates.reference_uris or existing.reference_uris,
            created_at=existing.created_at,
            updated_at=datetime.now(),
        )
        self._core_context.upsert_industry_term(store_term, tenant=tenant, user=user)
        return self.get(term_id, tenant=tenant, user=user)

    def link(
        self,
        term_id: str,
        related_term_ids: list[str],
        *,
        relationship: str = "related",
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Link an industry term to other related terms.

        Args:
            term_id: Identifier of the term to link from.
            related_term_ids: List of term IDs to link to.
            relationship: Type of relationship ("related", "synonym", "antonym").
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the term is not found.
            PermissionError: If the user lacks write permissions.
        """
        self._core_context.link_industry_terms(
            term_id,
            related_term_ids,
            relationship=relationship,
            tenant=tenant,
            user=user,
        )

    def delete(
        self,
        term_id: str,
        *,
        tenant: TenantContext,
        user: UserContext,
    ) -> None:
        """Delete an industry term.

        Args:
            term_id: Identifier of the term to delete.
            tenant: Tenant context for isolation.
            user: User context for permissions.

        Raises:
            KeyError: If the term is not found.
            PermissionError: If the user lacks delete permissions.
        """
        self._core_context.delete_industry_term(term_id, tenant=tenant, user=user)


# =============================================================================
# BusinessClient (Facade)
# =============================================================================


class BusinessClient:
    """High-level business client for XLake.

    The semantic and knowledge layer of XLake, owning everything related
    to business meaning, domain knowledge, schema semantics, KPI definitions,
    relationships, and conversational knowledge.

    Sub-clients:
    - `kpi`: Define and retrieve KPI/metric definitions
    - `schema`: Manage schema semantics and relationships
    - `facts`: Store and retrieve business facts
    - `semantic`: Semantic search and graph operations
    - `conversation`: Conversation context and state
    - `knowledge`: Manage domain knowledge nuggets
    - `industry`: Manage industry-specific terms and definitions

    Example:
        ```python
        biz = BusinessClient(stores)
        kpis = biz.kpi.list(tenant=tenant, user=user)
        graph = biz.semantic.graph("sales.revenue", tenant=tenant, user=user)
        context = biz.conversation.get_context("thread_123", tenant=tenant, user=user)
        nuggets = biz.knowledge.search("coffee processing", tenant=tenant, user=user)
        terms = biz.industry.search("arabica", industries=["coffee"], tenant=tenant, user=user)
        ```
    """

    def __init__(
        self,
        context_store: CustomerContextStore,
        app_logic_store: CustomerAppLogicStore,
        core_context_store: CoreContextStore,
        external_store: CoreExternalSourceStore | None = None,
    ) -> None:
        """Initialize the BusinessClient.

        Args:
            context_store: CustomerContextStore instance.
            app_logic_store: CustomerAppLogicStore instance.
            core_context_store: CoreContextStore instance.
            external_store: Optional CoreExternalSourceStore instance.
        """
        self.kpi = KPIBusinessClient(
            core_context_store=core_context_store,
            app_logic_store=app_logic_store,
        )
        self.schema = SchemaBusinessClient(
            context_store=context_store,
        )
        self.facts = FactsBusinessClient(
            context_store=context_store,
            core_context_store=core_context_store,
        )
        self.semantic = SemanticBusinessClient(
            context_store=context_store,
            core_context_store=core_context_store,
            external_store=external_store,
        )
        self.conversation = ConversationBusinessClient(
            app_logic_store=app_logic_store,
        )
        self.knowledge = KnowledgeBusinessClient(
            core_context_store=core_context_store,
        )
        self.industry = IndustryBusinessClient(
            core_context_store=core_context_store,
        )
