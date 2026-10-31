"""Add Level 2 columns to databases created before them. create_all only creates missing tables."""
from sqlalchemy import text
from sqlalchemy.engine import Connection

_COLUMNS = (
    ("audit_entries", "user_id", "VARCHAR"),
    ("case_history", "user_id", "VARCHAR"),
    ("cases", "risk_original", "VARCHAR"),
    ("cases", "risk_reason", "VARCHAR"),
    ("cases", "risk_changed_by", "VARCHAR"),
    ("cases", "priority_score", "INTEGER DEFAULT 0"),
    ("cases", "priority_parts", "JSON"),
    ("cases", "needs_review", "BOOLEAN DEFAULT FALSE"),
    ("cases", "conclusion", "VARCHAR"),
    ("cases", "split_from", "VARCHAR"),
)


def add_missing_columns(conn: Connection) -> None:
    if conn.dialect.name != "postgresql":
        return  # SQLite is only used by tests, on a fresh schema
    for table, column, ddl in _COLUMNS:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}"))
