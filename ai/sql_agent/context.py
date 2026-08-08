"""Conversation context — resolve follow-ups without repeating prior context."""

from __future__ import annotations

import re
from typing import Any


def _normalize_history(history: list[Any] | None) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    if not history:
        return turns
    for item in history:
        if isinstance(item, dict):
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "").strip()
        else:
            role = str(getattr(item, "role", "") or "").strip().lower()
            content = str(getattr(item, "content", "") or "").strip()
        if role in ("user", "assistant") and content:
            turns.append({"role": role, "content": content})
    return turns[-8:]


def _last_user_topic(history: list[dict[str, str]]) -> str | None:
    for turn in reversed(history):
        if turn["role"] == "user":
            return turn["content"]
    return None


def _last_assistant_snippet(history: list[dict[str, str]], *, max_chars: int = 600) -> str | None:
    for turn in reversed(history):
        if turn["role"] == "assistant":
            text = turn["content"].strip()
            return text[:max_chars]
    return None


_FOLLOW_UP_CUES = re.compile(
    r"^\s*("
    r"what\s+about|"
    r"how\s+about|"
    r"and\s+(the\s+)?|"
    r"same\s+(for|with)|"
    r"also\s+|"
    r"now\s+|"
    r"those|these|that|it|them|"
    r"the\s+same|"
    r"failed\s*\??$|"
    r"passed\s*\??$|"
    r"yield\s*\??$"
    r")",
    re.IGNORECASE,
)

_SHORT_METRIC = re.compile(
    r"^\s*(passed|failed|yield|total|production|summary)\s*\??\s*$",
    re.IGNORECASE,
)


def needs_context_resolution(question: str) -> bool:
    q = question.strip()
    if len(q.split()) <= 4 and _FOLLOW_UP_CUES.search(q):
        return True
    if _SHORT_METRIC.match(q):
        return True
    if re.search(r"\b(it|that|those|them|this)\b", q, re.I) and len(q.split()) <= 12:
        return True
    return False


def resolve_contextual_question(
    question: str,
    history: list[Any] | None = None,
) -> str:
    """
    Expand short / referential follow-ups using prior turns.

    Example: prior "How many passed wafers?" + "and failed?" →
    "How many failed wafers? (follow-up to: How many passed wafers?)"
    """
    cleaned = (question or "").strip()
    turns = _normalize_history(history)
    if not cleaned or not turns or not needs_context_resolution(cleaned):
        return cleaned

    prior = _last_user_topic(turns)
    prior_answer = _last_assistant_snippet(turns)
    if not prior:
        return cleaned

    lower = cleaned.lower().strip().rstrip("?")

    # Metric-only follow-ups after a KPI ask
    if _SHORT_METRIC.match(cleaned) or re.match(
        r"^\s*(and\s+)?(what\s+about\s+)?(passed|failed|yield|total|production)\s*\??\s*$",
        cleaned,
        re.I,
    ):
        metric = re.sub(r"^(and\s+|what\s+about\s+|how\s+about\s+)", "", lower, flags=re.I).strip()
        if "fail" in metric:
            return "How many failed wafers?"
        if "pass" in metric:
            return "How many passed wafers?"
        if "yield" in metric:
            return "What is the overall yield?"
        if "total" in metric or "production" in metric:
            return "What is the total production?"

    # Generic referential follow-up
    parts = [
        f"{cleaned}",
        "",
        f"(Conversation context — previous question: {prior})",
    ]
    if prior_answer:
        parts.append(f"(Previous answer summary: {prior_answer[:280]})")
    return "\n".join(parts)


def history_for_prompt(history: list[Any] | None, *, max_turns: int = 4) -> str:
    turns = _normalize_history(history)[-max_turns:]
    if not turns:
        return ""
    lines = ["Recent conversation:"]
    for turn in turns:
        role = "User" if turn["role"] == "user" else "Assistant"
        lines.append(f"- {role}: {turn['content'][:240]}")
    return "\n".join(lines)
