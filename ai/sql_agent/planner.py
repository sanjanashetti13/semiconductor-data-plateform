"""Question classification for the planning-based SQL Agent.

Pipeline step 1: Intent Classification (WHAT)
  KPI | Metadata | Schema | Business Understanding | Analytical | Knowledge | Smalltalk
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ai.sql_agent.intent import (
    QuestionIntent,
    classify_intent,
)
from ai.sql_agent.response_mode import ResponseMode, classify_response_mode


class QuestionCategory(str, Enum):
    """Execution categories used by the agent handlers."""

    KPI = "kpi"
    METADATA = "metadata"
    SCHEMA = "schema"
    BUSINESS_UNDERSTANDING = "business_understanding"
    BUSINESS_REASONING = "business_reasoning"
    ANALYTICAL = "analytical"
    KNOWLEDGE = "knowledge"
    SMALLTALK = "smalltalk"
    # Aliases for older call sites / API consumers
    DATABASE_UNDERSTANDING = "business_understanding"
    DATA_ANALYSIS = "analytical"


class MetadataIntent(str, Enum):
    LIST_TABLES = "list_tables"
    LIST_VIEWS = "list_views"
    LIST_COLUMNS = "list_columns"
    DESCRIBE_SCHEMA = "describe_schema"
    EXPLAIN_ALL = "explain_all"
    ROW_COUNTS = "row_counts"
    PRIMARY_KEYS = "primary_keys"
    FOREIGN_KEYS = "foreign_keys"
    INDEXES = "indexes"
    RELATIONSHIPS = "relationships"
    SAMPLE_ROWS = "sample_rows"


@dataclass(frozen=True)
class Plan:
    """Planner output consumed by the Executor."""

    category: QuestionCategory
    question: str
    intent: QuestionIntent = QuestionIntent.ANALYTICAL
    metadata_intent: MetadataIntent | None = None
    target_table: str | None = None
    response_mode: ResponseMode = ResponseMode.DIRECT


_META_PATTERNS: list[tuple[MetadataIntent, re.Pattern[str]]] = [
    (
        MetadataIntent.SAMPLE_ROWS,
        re.compile(
            r"\b(sample\s+rows?|show\s+sample|preview\s+rows?|top\s+\d+\s+rows?|"
            r"example\s+rows?|first\s+\d+\s+rows?)\b",
            re.I,
        ),
    ),
    (
        MetadataIntent.EXPLAIN_ALL,
        re.compile(
            r"\b(explain\s+(every|all|each)\s+tables?|describe\s+(every|all|each)\s+tables?|"
            r"what\s+does\s+each\s+table\s+contain)\b",
            re.I,
        ),
    ),
    (
        MetadataIntent.LIST_VIEWS,
        re.compile(r"\b(list|show|get)\b.*\bviews?\b|\bviews?\b.*\b(list|show)\b", re.I),
    ),
    (
        MetadataIntent.LIST_TABLES,
        re.compile(
            r"\b(list|show|get)\b.*\btables?\b|"
            r"\btables?\b.*\b(list|show|exist|available)\b|"
            r"\bwhat\s+tables?\b|"
            r"\btables?\s+exist\b|"
            r"\bwhich\s+tables?\b",
            re.I,
        ),
    ),
    (
        MetadataIntent.ROW_COUNTS,
        re.compile(r"\b(row counts?|how many rows|table sizes?|largest tables?)\b", re.I),
    ),
    (MetadataIntent.PRIMARY_KEYS, re.compile(r"\bprimary\s+keys?\b", re.I)),
    (MetadataIntent.FOREIGN_KEYS, re.compile(r"\bforeign\s+keys?\b", re.I)),
    (MetadataIntent.INDEXES, re.compile(r"\bindexes?\b|\bindices\b", re.I)),
    (MetadataIntent.RELATIONSHIPS, re.compile(r"\brelationships?\b|\breferential\b", re.I)),
    (
        MetadataIntent.LIST_COLUMNS,
        re.compile(
            r"\b(list|show|get)\b.*\bcolumns?\b|"
            r"\bcolumns?\b.*\b(for|of|in)\b|"
            r"\bdescribe\b.*\b(table|view)\b|"
            r"\bdescribe\s+[A-Za-z_][\w.]+\b",
            re.I,
        ),
    ),
]

_TABLE_HINT = re.compile(
    r"(?:table|view|from|for|of|in)\s+[\"'`]?([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)?)[\"'`]?",
    re.IGNORECASE,
)

_STOP_TABLE_TOKENS = {
    "contain",
    "contains",
    "exist",
    "exists",
    "available",
    "here",
    "there",
    "the",
    "a",
    "an",
    "this",
    "that",
    "these",
    "those",
    "with",
    "and",
    "or",
    "purpose",
    "columns",
    "rows",
    "every",
    "all",
    "each",
}


def _extract_table(question: str) -> str | None:
    match = _TABLE_HINT.search(question)
    if match:
        token = match.group(1).strip()
        if token.lower() not in _STOP_TABLE_TOKENS:
            return token
    describe = re.search(
        r"\bdescribe\s+[\"'`]?([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)?)[\"'`]?",
        question,
        re.IGNORECASE,
    )
    if describe:
        token = describe.group(1).strip()
        if token.lower() not in _STOP_TABLE_TOKENS:
            return token
    return None


def _metadata_intent_for(question: str) -> MetadataIntent:
    for intent, pattern in _META_PATTERNS:
        if pattern.search(question):
            return intent
    return MetadataIntent.DESCRIBE_SCHEMA


def classify_question(question: str) -> Plan:
    """Classify WHAT the user is asking before any SQL generation."""
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    # Strip conversation-context appendix before intent match
    intent_text = cleaned.split("(Conversation context")[0].strip() or cleaned
    intent = classify_intent(intent_text)

    if intent == QuestionIntent.SMALLTALK:
        return Plan(
            category=QuestionCategory.SMALLTALK,
            question=cleaned,
            intent=intent,
            response_mode=ResponseMode.DIRECT,
        )

    if intent == QuestionIntent.KNOWLEDGE:
        return Plan(
            category=QuestionCategory.KNOWLEDGE,
            question=cleaned,
            intent=intent,
            response_mode=ResponseMode.STANDARD,
        )

    if intent == QuestionIntent.KPI:
        return Plan(
            category=QuestionCategory.KPI,
            question=cleaned,
            intent=intent,
            response_mode=classify_response_mode(intent_text),
        )

    if intent == QuestionIntent.BUSINESS_REASONING:
        return Plan(
            category=QuestionCategory.BUSINESS_REASONING,
            question=cleaned,
            intent=intent,
            response_mode=ResponseMode.DETAILED,
        )

    if intent == QuestionIntent.BUSINESS_UNDERSTANDING:
        return Plan(
            category=QuestionCategory.BUSINESS_UNDERSTANDING,
            question=cleaned,
            intent=intent,
            response_mode=ResponseMode.STANDARD,
        )

    if intent == QuestionIntent.SCHEMA:
        return Plan(
            category=QuestionCategory.SCHEMA,
            question=cleaned,
            intent=intent,
            metadata_intent=MetadataIntent.EXPLAIN_ALL,
            response_mode=ResponseMode.STANDARD,
        )

    if intent == QuestionIntent.METADATA:
        meta = _metadata_intent_for(intent_text)
        return Plan(
            category=QuestionCategory.METADATA,
            question=cleaned,
            intent=intent,
            metadata_intent=meta,
            target_table=_extract_table(intent_text),
            response_mode=ResponseMode.DIRECT,
        )

    return Plan(
        category=QuestionCategory.ANALYTICAL,
        question=cleaned,
        intent=intent,
        response_mode=classify_response_mode(intent_text),
    )
