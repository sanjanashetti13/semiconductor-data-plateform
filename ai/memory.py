"""In-memory conversation / schema memory for the multi-agent platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionMemory:
    """Per-session working memory (never persisted to disk)."""

    session_id: str
    turns: list[dict[str, str]] = field(default_factory=list)
    last_sql: str | None = None
    last_sql_result: str | None = None
    last_topic: str | None = None
    schema_summary: str | None = None
    database: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


_MEMORY: dict[str, SessionMemory] = {}


def get_memory(session_id: str | None) -> SessionMemory | None:
    if not session_id:
        return None
    return _MEMORY.get(session_id)


def ensure_memory(session_id: str, *, database: str | None = None) -> SessionMemory:
    mem = _MEMORY.get(session_id)
    if mem is None:
        mem = SessionMemory(session_id=session_id, database=database)
        _MEMORY[session_id] = mem
    elif database:
        mem.database = database
    return mem


def clear_memory(session_id: str) -> None:
    _MEMORY.pop(session_id, None)


def remember_turn(
    session_id: str | None,
    *,
    question: str,
    answer: str,
    sql: str | None = None,
    sql_result: str | None = None,
    topic: str | None = None,
) -> None:
    if not session_id:
        return
    mem = ensure_memory(session_id)
    mem.turns.append({"role": "user", "content": question})
    mem.turns.append({"role": "assistant", "content": answer})
    mem.turns = mem.turns[-16:]
    if sql:
        mem.last_sql = sql
    if sql_result:
        mem.last_sql_result = sql_result[:4_000]
    if topic:
        mem.last_topic = topic


def memory_context_text(session_id: str | None, *, max_turns: int = 6) -> str:
    mem = get_memory(session_id)
    if not mem or not mem.turns:
        return ""
    lines = ["Session memory:"]
    if mem.database:
        lines.append(f"- Database: {mem.database}")
    if mem.last_topic:
        lines.append(f"- Last topic: {mem.last_topic}")
    if mem.last_sql:
        lines.append(f"- Last SQL: {mem.last_sql[:240]}")
    for turn in mem.turns[-max_turns:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"- {role}: {turn['content'][:220]}")
    return "\n".join(lines)
