"""Formatter — turns execution results into Copilot-style answers."""

from __future__ import annotations

from ai.sql_agent.executor import ExecutionBundle, QueryResult
from ai.sql_agent.planner import MetadataIntent, QuestionCategory
from ai.sql_agent.response_mode import ResponseMode


METADATA_FOLLOW_UPS = [
    "List the tables in this database",
    "Show primary keys",
    "Summarize what this database appears to contain",
]

ANALYSIS_FOLLOW_UPS = [
    "List the tables in this database",
    "Show a sample of 10 rows from an important table",
    "Summarize what this database appears to contain",
]

UNDERSTANDING_FOLLOW_UPS = [
    "List the tables in this database",
    "Show row counts",
    "Show primary keys and foreign keys",
]


def is_scalar_result(result: QueryResult) -> bool:
    """True when the query returned a single cell (typical count/yield)."""
    return (
        not result.error
        and len(result.columns) == 1
        and len(result.rows) == 1
        and result.rows[0]
        and result.rows[0][0] is not None
    )


def format_rows_markdown(result: QueryResult, *, max_rows: int = 25) -> str:
    if result.error:
        return f"_{result.error}_"
    if not result.columns:
        return "_No columns returned._"
    header = "| " + " | ".join(str(c) for c in result.columns) + " |"
    sep = "| " + " | ".join("---" for _ in result.columns) + " |"
    lines = [header, sep]
    rows = result.rows[:max_rows]
    if not rows:
        lines.append("| " + " | ".join("—" for _ in result.columns) + " |")
    else:
        for row in rows:
            cells = [str(v) if v is not None else "NULL" for v in row]
            lines.append("| " + " | ".join(cells) + " |")
    if len(result.rows) > max_rows:
        lines.append(f"\n_Showing {max_rows} of {len(result.rows)} rows._")
    return "\n".join(lines)


def format_name_list(result: QueryResult, *, name_indexes: tuple[int, ...] = (0, 1)) -> str:
    """Render schema objects as a simple Copilot-style bullet list."""
    if result.error:
        return f"_{result.error}_"
    if not result.rows:
        return "_None found._"
    lines: list[str] = []
    for row in result.rows:
        parts = [str(row[i]) for i in name_indexes if i < len(row) and row[i] is not None]
        if len(parts) >= 2:
            lines.append(f"- `{parts[0]}.{parts[1]}`")
        elif parts:
            lines.append(f"- `{parts[0]}`")
    return "\n".join(lines) if lines else "_None found._"


def format_metadata_answer(intent: MetadataIntent | None, bundle: ExecutionBundle) -> str:
    """Concise Copilot-style answer for Metadata questions (no SQL)."""
    intent = intent or MetadataIntent.DESCRIBE_SCHEMA
    title = {
        MetadataIntent.LIST_TABLES: "Tables",
        MetadataIntent.LIST_VIEWS: "Views",
        MetadataIntent.LIST_COLUMNS: "Columns",
        MetadataIntent.DESCRIBE_SCHEMA: "Schema overview",
        MetadataIntent.ROW_COUNTS: "Row counts",
        MetadataIntent.PRIMARY_KEYS: "Primary keys",
        MetadataIntent.FOREIGN_KEYS: "Foreign keys",
        MetadataIntent.INDEXES: "Indexes",
        MetadataIntent.RELATIONSHIPS: "Relationships",
    }.get(intent, "Metadata")

    if intent == MetadataIntent.LIST_TABLES and bundle.results:
        return f"**{title}**\n\n{format_name_list(bundle.results[0], name_indexes=(0, 1))}"
    if intent == MetadataIntent.LIST_VIEWS and bundle.results:
        return f"**{title}**\n\n{format_name_list(bundle.results[0], name_indexes=(0, 1))}"

    parts = [f"**{title}**", ""]
    for result in bundle.results:
        if len(bundle.results) > 1:
            parts.append(f"### {result.label}")
        parts.append(format_rows_markdown(result))
        parts.append("")
    return "\n".join(parts).strip()


def format_analysis_answer(
    *,
    narrative: str,
    sql: str,
    result: QueryResult,
    mode: ResponseMode,
) -> str:
    """
    Single user-facing answer — no duplicated Answer/Explanation blocks.

    SQL stays on the API payload for Developer Mode only.
    """
    del sql
    text = narrative.strip()
    if not text:
        text = "_No answer generated._"

    if mode == ResponseMode.DIRECT:
        # One response only — never attach Result/Explanation duplicates.
        return text

    # Standard / Detailed: LLM already structured; avoid appending raw tables
    # that restate the same numbers.
    return text


def format_analysis_failure(reason: str) -> str:
    from ai.sql_agent.errors import FRIENDLY_QUERY_ERROR, sanitize_user_message

    why = sanitize_user_message(reason, fallback=FRIENDLY_QUERY_ERROR)
    return (
        "I couldn't complete that analysis.\n\n"
        f"{why}\n\n"
        "You can try:\n"
        "- List the tables in this database\n"
        "- Summarize what this database appears to contain\n"
        "- Ask a simpler count or filter question"
    )


def format_smalltalk(database: str, table_names: list[str]) -> str:
    preview = ", ".join(f"`{n}`" for n in table_names[:8]) or "_none listed yet_"
    more = f" (+{len(table_names) - 8} more)" if len(table_names) > 8 else ""
    return (
        f"Connected to **{database}** with {len(table_names)} tables/views ready.\n\n"
        f"Examples: {preview}{more}\n\n"
        "Ask metadata questions (list tables), request a database overview, "
        "or ask analytical questions (counts, averages, top-N)."
    )


KNOWLEDGE_FOLLOW_UPS = [
    "What is the SECOM dataset?",
    "What is a wafer?",
    "How many wafers passed?",
]


def follow_ups_for(category: QuestionCategory) -> list[str]:
    if category == QuestionCategory.METADATA:
        return list(METADATA_FOLLOW_UPS)
    if category == QuestionCategory.DATABASE_UNDERSTANDING:
        return list(UNDERSTANDING_FOLLOW_UPS)
    if category == QuestionCategory.KNOWLEDGE:
        return list(KNOWLEDGE_FOLLOW_UPS)
    if category == QuestionCategory.KPI:
        return [
            "How many failed?",
            "What is the overall yield?",
            "Show the production summary",
        ]
    return list(ANALYSIS_FOLLOW_UPS)


def compact_result_for_prompt(result: QueryResult, mode: ResponseMode) -> str:
    """Send a small result payload to the LLM based on response mode."""
    if is_scalar_result(result):
        value = result.rows[0][0]
        col = result.columns[0]
        return f"scalar_column={col}\nscalar_value={value}"

    max_rows = 5 if mode == ResponseMode.DIRECT else 15 if mode == ResponseMode.STANDARD else 25
    return result.as_text(max_rows=max_rows)
