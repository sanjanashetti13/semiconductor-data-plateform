"""Lightweight conversation helpers for the orchestration layer."""

from __future__ import annotations

from typing import Any

from ai.sql_agent.context import (
    history_for_prompt,
    needs_context_resolution,
    resolve_contextual_question,
)


def resolve_question(question: str, history: list[Any] | None = None) -> str:
    """Expand follow-ups using prior turns (reuses SQL-agent context helpers)."""
    return resolve_contextual_question(question, history)


def format_history(history: list[Any] | None = None) -> str:
    return history_for_prompt(history)


def is_follow_up(question: str) -> bool:
    return needs_context_resolution(question)


__all__ = [
    "format_history",
    "is_follow_up",
    "resolve_question",
]
