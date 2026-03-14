from __future__ import annotations

from typing import Protocol

from xlake.models.schema import DataSchema, Fact


class SchemaEmbedder(Protocol):
    def get_embeddings(self, texts: list[str]) -> list[list[float]]: ...

    def embed_schema(
        self,
        *,
        schema_model: DataSchema,
        tenant_id: str,
        schema_id: str,
        schema_version: int,
        schema_uri: str,
        facts_by_entity: dict[str, list[Fact]] | None,
    ) -> list[dict]: ...
    def _embed_texts(self, texts: list[str]) -> list[list[float]]: ...


def _iter_field_texts(schema_model: DataSchema) -> dict[str, str]:
    texts: dict[str, str] = {}
    for db in schema_model.databases:
        for tbl in db.tables:
            for fld in tbl.fields:
                fid = f"{db.name}:{tbl.name}.{fld.name}"
                parts = [
                    f"Field: {fid}",
                    f"Type: {fld.type}",
                    f"Nullable: {str(bool(fld.nullable)).lower()}",
                    f"Description: {fld.description or ''}",
                    f"Table: {tbl.name}",
                    f"Database: {db.name}",
                ]
                texts[fid] = " | ".join(parts)
    return texts


class _BaseEmbedder:
    def __init__(self, model_name: str = "fastembed:BAAI/bge-small-en-v1.5") -> None:
        self._model_name = model_name

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._embed_texts(texts)

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # For now only FastEmbed is supported; use model_name to select
        try:
            from fastembed import TextEmbedding  # type: ignore
        except Exception:
            return []
        # model_name may be "fastembed:BAAI/bge-small-en-v1.5"
        name = (
            self._model_name.split(":", 1)[1]
            if ":" in self._model_name
            else self._model_name
        )
        model = TextEmbedding(model_name=name)
        vectors: list[list[float]] = []
        for vec in model.embed(texts):
            vectors.append([float(x) for x in list(vec)])
        return vectors


class FieldsOnlyEmbedder(_BaseEmbedder):
    def embed_schema(
        self,
        *,
        schema_model: DataSchema,
        tenant_id: str,
        schema_id: str,
        schema_version: int,
        schema_uri: str,
        facts_by_entity: dict[str, list[Fact]] | None,
    ) -> list[dict]:
        field_texts = _iter_field_texts(schema_model)
        if not field_texts:
            return []
        eids = list(field_texts.keys())
        texts = [field_texts[eid] for eid in eids]
        vectors = self.get_embeddings(texts)
        if not vectors:
            return []
        points: list[dict] = []
        for eid, vec in zip(eids, vectors, strict=False):
            points.append({
                "id": f"{schema_id}:{schema_version}:{eid}",
                "vector": vec,
                "payload": {
                    "tenant_id": tenant_id,
                    "schema_id": schema_id,
                    "schema_version": schema_version,
                    "entity_type": "field",
                    "entity_id": eid,
                    "schema_uri": schema_uri,
                    "source": "schema",
                    "model": self._model_name,
                },
            })
        return points


class FieldsAndFactsEmbedder(_BaseEmbedder):
    def embed_schema(
        self,
        *,
        schema_model: DataSchema,
        tenant_id: str,
        schema_id: str,
        schema_version: int,
        schema_uri: str,
        facts_by_entity: dict[str, list[Fact]] | None,
    ) -> list[dict]:
        points: list[dict] = []
        # Fields
        points.extend(
            FieldsOnlyEmbedder(self._model_name).embed_schema(
                schema_model=schema_model,
                tenant_id=tenant_id,
                schema_id=schema_id,
                schema_version=schema_version,
                schema_uri=schema_uri,
                facts_by_entity=None,
            )
        )
        # Facts as separate points
        if facts_by_entity:
            texts: list[str] = []
            ids: list[tuple[str, str]] = []  # (entity_id, fact_id)
            for eid, facts in facts_by_entity.items():
                for f in facts or []:
                    tags = f.tags or []
                    t = " | ".join([
                        f"Fact: {f.text}",
                        f"Entity: {eid}",
                        f"Date: {(f.date.isoformat() if f.date else '')}",
                        f"Source: {f.source or ''}",
                        f"Tags: {', '.join(tags) if tags else ''}",
                    ])
                    texts.append(t)
                    ids.append((eid, f.fact_id))
            if texts:
                vectors = self.get_embeddings(texts)
                for (eid, fid), vec in zip(ids, vectors, strict=False):
                    points.append({
                        "id": f"{schema_id}:{schema_version}:{eid}:{fid}",
                        "vector": vec,
                        "payload": {
                            "tenant_id": tenant_id,
                            "schema_id": schema_id,
                            "schema_version": schema_version,
                            "entity_type": "fact",
                            "entity_id": eid,
                            "fact_id": fid,
                            "schema_uri": schema_uri,
                            "source": "schema",
                            "model": self._model_name,
                        },
                    })
        return points
