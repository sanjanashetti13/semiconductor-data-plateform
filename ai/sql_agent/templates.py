"""Predefined read-only SQL templates for Metadata questions (no LLM SQL)."""

from __future__ import annotations

from ai.sql_agent.planner import MetadataIntent

# All templates are SELECT-only and safe for Azure SQL / SQL Server.


def sql_list_tables() -> str:
    return """
SELECT TABLE_SCHEMA AS [schema], TABLE_NAME AS [table], TABLE_TYPE AS [type]
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
ORDER BY TABLE_SCHEMA, TABLE_NAME
""".strip()


def sql_list_views() -> str:
    return """
SELECT TABLE_SCHEMA AS [schema], TABLE_NAME AS [view]
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'VIEW'
  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
ORDER BY TABLE_SCHEMA, TABLE_NAME
""".strip()


def sql_list_columns(schema: str | None = None, table: str | None = None) -> str:
    if schema and table:
        return f"""
SELECT COLUMN_NAME AS [column], DATA_TYPE AS [data_type],
       IS_NULLABLE AS [nullable], CHARACTER_MAXIMUM_LENGTH AS [max_length]
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = N'{_escape(schema)}' AND TABLE_NAME = N'{_escape(table)}'
ORDER BY ORDINAL_POSITION
""".strip()
    if table:
        return f"""
SELECT TABLE_SCHEMA AS [schema], TABLE_NAME AS [table],
       COLUMN_NAME AS [column], DATA_TYPE AS [data_type], IS_NULLABLE AS [nullable]
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'{_escape(table)}'
  AND TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
""".strip()
    return """
SELECT TABLE_SCHEMA AS [schema], TABLE_NAME AS [table],
       COLUMN_NAME AS [column], DATA_TYPE AS [data_type]
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
""".strip()


def sql_describe_schema() -> str:
    return """
SELECT t.TABLE_SCHEMA AS [schema], t.TABLE_NAME AS [object], t.TABLE_TYPE AS [type],
       COUNT(c.COLUMN_NAME) AS column_count
FROM INFORMATION_SCHEMA.TABLES t
LEFT JOIN INFORMATION_SCHEMA.COLUMNS c
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
  AND t.TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME, t.TABLE_TYPE
ORDER BY t.TABLE_TYPE, t.TABLE_SCHEMA, t.TABLE_NAME
""".strip()


def sql_primary_keys() -> str:
    return """
SELECT tc.TABLE_SCHEMA AS [schema], tc.TABLE_NAME AS [table],
       kcu.COLUMN_NAME AS [column], tc.CONSTRAINT_NAME AS [constraint]
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
 AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
  AND tc.TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
ORDER BY tc.TABLE_SCHEMA, tc.TABLE_NAME, kcu.ORDINAL_POSITION
""".strip()


def sql_foreign_keys() -> str:
    return """
SELECT fk.TABLE_SCHEMA AS [from_schema], fk.TABLE_NAME AS [from_table],
       cu.COLUMN_NAME AS [from_column],
       pk.TABLE_SCHEMA AS [to_schema], pk.TABLE_NAME AS [to_table],
       pt.COLUMN_NAME AS [to_column],
       fk.CONSTRAINT_NAME AS [constraint]
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS fk
  ON rc.CONSTRAINT_NAME = fk.CONSTRAINT_NAME AND rc.CONSTRAINT_SCHEMA = fk.CONSTRAINT_SCHEMA
JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS pk
  ON rc.UNIQUE_CONSTRAINT_NAME = pk.CONSTRAINT_NAME
 AND rc.UNIQUE_CONSTRAINT_SCHEMA = pk.CONSTRAINT_SCHEMA
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE cu
  ON fk.CONSTRAINT_NAME = cu.CONSTRAINT_NAME AND fk.TABLE_SCHEMA = cu.TABLE_SCHEMA
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE pt
  ON pk.CONSTRAINT_NAME = pt.CONSTRAINT_NAME AND pk.TABLE_SCHEMA = pt.TABLE_SCHEMA
 AND cu.ORDINAL_POSITION = pt.ORDINAL_POSITION
WHERE fk.TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest')
ORDER BY fk.TABLE_SCHEMA, fk.TABLE_NAME
""".strip()


def sql_indexes() -> str:
    return """
SELECT OBJECT_SCHEMA_NAME(i.object_id) AS [schema],
       OBJECT_NAME(i.object_id) AS [table],
       i.name AS [index_name],
       i.type_desc AS [index_type],
       i.is_unique AS [is_unique],
       i.is_primary_key AS [is_primary_key]
FROM sys.indexes i
JOIN sys.tables t ON i.object_id = t.object_id
WHERE i.name IS NOT NULL
ORDER BY [schema], [table], [index_name]
""".strip()


def sql_relationships() -> str:
    # Relationships are foreign-key based for SQL Server/Azure SQL.
    return sql_foreign_keys()


def sql_sample_rows(schema: str, table: str, n: int = 3) -> str:
    n = max(1, min(int(n), 10))
    return (
        f"SELECT TOP ({n}) * "
        f"FROM [{_escape(schema)}].[{_escape(table)}]"
    )


def sql_row_count(schema: str, table: str) -> str:
    return (
        f"SELECT COUNT_BIG(*) AS row_count "
        f"FROM [{_escape(schema)}].[{_escape(table)}]"
    )


def resolve_metadata_sql(
    intent: MetadataIntent,
    *,
    target_table: str | None = None,
) -> str:
    """Map a metadata intent to a predefined SELECT template."""
    schema, table = _split_table(target_table)

    if intent == MetadataIntent.LIST_TABLES:
        return sql_list_tables()
    if intent == MetadataIntent.LIST_VIEWS:
        return sql_list_views()
    if intent == MetadataIntent.LIST_COLUMNS:
        return sql_list_columns(schema, table)
    if intent == MetadataIntent.DESCRIBE_SCHEMA:
        return sql_describe_schema()
    if intent == MetadataIntent.PRIMARY_KEYS:
        return sql_primary_keys()
    if intent == MetadataIntent.FOREIGN_KEYS:
        return sql_foreign_keys()
    if intent == MetadataIntent.INDEXES:
        return sql_indexes()
    if intent == MetadataIntent.RELATIONSHIPS:
        return sql_relationships()
    if intent == MetadataIntent.ROW_COUNTS:
        # Row counts use a multi-step executor path; this is a fallback listing.
        return sql_list_tables()
    return sql_describe_schema()


def _split_table(target: str | None) -> tuple[str | None, str | None]:
    if not target:
        return None, None
    parts = target.replace("[", "").replace("]", "").split(".")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, parts[0]


def _escape(value: str) -> str:
    return value.replace("'", "''")
