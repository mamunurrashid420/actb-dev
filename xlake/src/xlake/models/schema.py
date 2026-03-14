"""Pydantic models and helpers for versioned JSON schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FieldSchema(BaseModel):
    """Column/field definition."""

    name: str
    type: Literal[
        "int", "float", "decimal", "text", "bool", "date", "timestamp", "json", "other"
    ] = "other"
    nullable: bool = False
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class TableSchema(BaseModel):
    """Table definition containing fields."""

    name: str
    description: str | None = None
    fields: list[FieldSchema] = Field(default_factory=list)


class DatabaseSchema(BaseModel):
    """Logical database/container of tables."""

    name: str
    tables: list[TableSchema] = Field(default_factory=list)


class DataSchema(BaseModel):
    """Top-level schema snapshot that is versioned immutably as JSON."""

    schema_id: str
    version: int
    name: str | None = None
    description: str | None = None
    databases: list[DatabaseSchema] = Field(default_factory=list)


# ---------------------------
# Helpers
# ---------------------------


def to_field_id(database: str, table: str, column: str) -> str:
    """Build canonical field identifier: <database>:<table>.<column>"""
    return f"{database}:{table}.{column}"


def parse_field_id(fid: str) -> tuple[str, str, str]:
    """Parse canonical field identifier into (database, table, column)."""
    db, rest = fid.split(":", 1)
    tbl, col = rest.split(".", 1)
    return db, tbl, col


def schema_from_json(json_str: str) -> DataSchema:
    """Deserialize JSON string to DataSchema."""
    return DataSchema.model_validate_json(json_str)


def schema_to_json(schema: DataSchema) -> str:
    """Serialize DataSchema to JSON string."""
    return schema.model_dump_json(indent=2, by_alias=False, exclude_none=True)


def iter_field_ids(schema: DataSchema) -> list[str]:
    """Enumerate canonical field identifiers for all fields in the schema."""
    ids: list[str] = []
    for db in schema.databases:
        for tbl in db.tables:
            for fld in tbl.fields:
                ids.append(to_field_id(db.name, tbl.name, fld.name))
    return ids


def normalize_schema_dict_to_model(obj: dict[str, Any]) -> DataSchema:
    """Best-effort conversion of a dictionary to a valid DataSchema.

    Accepts:
    - Preferred shape with 'databases'
    - Legacy shape with 'tables' at the root
    Missing `schema_id` and `version` are defaulted to 'unknown' and 1, respectively.
    """
    schema_id = obj.get("schema_id", "unknown")
    version = int(obj.get("version", 1))
    name = obj.get("name")
    description = obj.get("description")

    if "databases" in obj and isinstance(obj["databases"], list):
        databases: list[DatabaseSchema] = []
        for db_obj in obj["databases"]:
            db_name = db_obj.get("name", "default")
            tables_list = db_obj.get("tables", []) or []
            tables: list[TableSchema] = []
            for t in tables_list:
                t_name = t.get("name", "unknown_table")
                t_desc = t.get("description")
                fields_list = t.get("fields", []) or []
                fields: list[FieldSchema] = []
                for f in fields_list:
                    fields.append(
                        FieldSchema(
                            name=f.get("name", "unknown_field"),
                            type=f.get("type", "other"),
                            nullable=bool(f.get("nullable", False)),
                            description=f.get("description"),
                            tags=f.get("tags", []) or [],
                        )
                    )
                tables.append(
                    TableSchema(name=t_name, description=t_desc, fields=fields)
                )
            databases.append(DatabaseSchema(name=db_name, tables=tables))
        return DataSchema(
            schema_id=schema_id,
            version=version,
            name=name,
            description=description,
            databases=databases,
        )

    # Legacy: root-level 'tables'
    legacy_tables = obj.get("tables", []) or []
    tables: list[TableSchema] = []
    for t in legacy_tables:
        t_name = t.get("name", "unknown_table")
        t_desc = t.get("description")
        fields_list = t.get("fields", []) or []
        fields: list[FieldSchema] = []
        for f in fields_list:
            fields.append(
                FieldSchema(
                    name=f.get("name", "unknown_field"),
                    type=f.get("type", "other"),
                    nullable=bool(f.get("nullable", False)),
                    description=f.get("description"),
                    tags=f.get("tags", []) or [],
                )
            )
        tables.append(TableSchema(name=t_name, description=t_desc, fields=fields))
    return DataSchema(
        schema_id=schema_id,
        version=version,
        name=name,
        description=description,
        databases=[DatabaseSchema(name="default", tables=tables)],
    )


class FactCreate(BaseModel):
    """User-provided Fact payload without identifiers."""

    text: str
    date: datetime | None = None
    source: str | None = None
    tags: list[str] | None = None


class Fact(FactCreate):
    """Stored Fact with identifiers."""

    fact_id: str
    entity_id: str
