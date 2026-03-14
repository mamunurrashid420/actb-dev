"""Database connection testing utilities."""

from typing import Any

import mysql.connector
import psycopg


def test_postgres(config: dict[str, Any]) -> None:
    """Raise an exception if Postgres connection fails."""
    conn = psycopg.connect(
        host=config["host"],
        port=config.get("port", 5432),
        dbname=config.get("database"),
        user=config.get("username"),
        password=config.get("password"),
        connect_timeout=5,
        sslmode=config.get("sslmode", "prefer"),
    )
    conn.close()


def test_mysql(config: dict[str, Any]) -> None:
    """Raise an exception if MySQL connection fails."""
    conn = mysql.connector.connect(
        host=config["host"],
        port=config.get("port", 3306),
        database=config.get("database"),
        user=config.get("username"),
        password=config.get("password"),
        connection_timeout=5,
        ssl_disabled=not config.get("ssl", False),
    )
    conn.close()


def test_connection(db_type: str, config: dict[str, Any]) -> None:
    """Test a database connection based on type."""
    if db_type == "postgres":
        test_postgres(config)
        return
    if db_type == "mysql":
        test_mysql(config)
        return
    raise ValueError(f"Unsupported database type: {db_type}")
