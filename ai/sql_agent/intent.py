"""Intent classification — factual SQL vs schema/business reasoning."""

from __future__ import annotations

import re
from enum import Enum


class QuestionIntent(str, Enum):
    """Primary question intents for the enterprise SQL analytics assistant."""

    KPI = "kpi"  # factual metrics → SQL
    METADATA = "metadata"
    SCHEMA = "schema"  # catalog all objects
    BUSINESS_UNDERSTANDING = "business_understanding"  # whole-DB description
    BUSINESS_REASONING = "business_reasoning"  # schema-grounded advice (no SQL)
    ANALYTICAL = "analytical"  # factual analysis → SQL
    KNOWLEDGE = "knowledge"
    SMALLTALK = "smalltalk"


_SMALLTALK = re.compile(
    r"^(hi|hello|hey|hiya|good\s+(morning|afternoon|evening)|thanks|thank\s+you|"
    r"ok|okay|yo|sup)[\s!.?]*$",
    re.IGNORECASE,
)

_KNOWLEDGE_PATTERNS = re.compile(
    r"\b("
    r"what\s+is\s+(the\s+)?secom(\s+dataset)?|"
    r"what\s+is\s+a\s+wafer|"
    r"what\s+(are|is)\s+a\s+(wafer|sensor|die|fab)\b|"
    r"explain\s+(semiconductor|wafer|secom|manufacturing|etl|bronze|silver|gold)\b|"
    r"what\s+is\s+semiconductor\s+manufacturing|"
    r"how\s+does\s+(semiconductor|wafer)\b|"
    r"tell\s+me\s+about\s+(secom|wafers?|semiconductor\s+manufacturing)|"
    r"project\s+knowledge|knowledge\s+base|"
    r"what\s+is\s+(bronze|silver|gold)\s+layer|"
    r"medallion\s+architecture|"
    r"what\s+does\s+(a\s+)?(sensor|wafer)\s+(measure|mean)"
    r")\b",
    re.IGNORECASE,
)

# Factual KPI asks only — must not catch "what influences yield"
_KPI_PATTERNS = re.compile(
    r"\b("
    r"how\s+many\s+(passed|failed|pass|fail|wafers?)(\s+wafers?)?|"
    r"number\s+of\s+(passed|failed|pass|fail|wafers?)|"
    r"(?:what\s+is\s+(the\s+)?)?overall\s+yield|"
    r"(?:what\s+is\s+(the\s+)?)?yield\s*(%|percentage|percent|rate)\b|"
    r"^yield\s*\??$|"
    r"^overall\s+yield\s*\??$|"
    r"passed(\s+wafers?)?\s*\??$|"
    r"failed(\s+wafers?)?\s*\??$|"
    r"how\s+many\s+passed|"
    r"how\s+many\s+failed|"
    r"pass\s+(rate|percentage|percent|%)|"
    r"fail(ure)?\s+(rate|percentage|percent|%)|"
    r"total\s+wafers?|total\s+production|overall\s+production|"
    r"production\s+summary|manufacturing\s+summary|"
    r"overall\s+(production\s+)?summary"
    r")\b",
    re.IGNORECASE,
)

# Schema-grounded reasoning / recommendations — NEVER SQL-only
_REASONING_PATTERNS = re.compile(
    r"\b("
    r"what\s+(factors?\s+)?(influence|affect|drive|impact)s?\b|"
    r"what\s+influences?\b|"
    r"how\s+(would|can|do)\s+(you\s+)?(reduce|improve|increase|decrease|fix)|"
    r"how\s+to\s+(reduce|improve|increase|fix)|"
    r"recommend(ation)?s?\b|"
    r"root\s+cause|"
    r"what\s+causes?\b|"
    r"why\s+(do|does|are|is|did)\b|"
    r"what\s+opportunities?\b|"
    r"machine\s+learning\s+opportunit|"
    r"ai\s+opportunit|"
    r"business\s+implications?|"
    r"how\s+should\s+(we|i|teams?)\b|"
    r"what\s+should\s+(we|i)\b|"
    r"leverage\s+(this\s+)?data|"
    r"reduce\s+failures?|"
    r"improve\s+yield|"
    r"factors?\s+influencing"
    r")\b",
    re.IGNORECASE,
)

_BUSINESS_UNDERSTANDING_PHRASES = (
    "what does this database contain",
    "what does the database contain",
    "what is the dataset about",
    "what is this dataset about",
    "what's the dataset about",
    "what is this data about",
    "what is the data about",
    "what is this database used for",
    "what is the database used for",
    "what is this data used for",
    "what is this db used for",
    "summarize what this database",
    "summarize this database",
    "summarize the database",
    "summarize this dataset",
    "summarize the dataset",
    "explain this database",
    "explain the database",
    "explain this dataset",
    "explain the dataset",
    "what is this database about",
    "what is the database about",
    "database overview",
    "overview of this database",
    "overview of the database",
    "what's in this database",
    "what is in this database",
    "describe this database",
    "describe the database",
    "describe this dataset",
    "describe the dataset",
    "tell me about this database",
    "tell me about the database",
    "tell me about this dataset",
    "tell me about the dataset",
    "business purpose of this",
    "purpose of this database",
    "purpose of this dataset",
    "what can i analyze",
    "what insights can i get",
    "complete solution",
    "end to end solution",
)

_SCHEMA_PATTERNS = re.compile(
    r"\b("
    r"explain\s+(every|all|each)\s+tables?|"
    r"explain\s+tables?|"
    r"describe\s+(every|all|each)\s+tables?|"
    r"what\s+does\s+each\s+table\s+contain|"
    r"what\s+objects?\s+exist|"
    r"which\s+objects?\s+exist|"
    r"list\s+(all\s+)?objects?|"
    r"show\s+(all\s+)?objects?|"
    r"what\s+(tables?\s+and\s+views?|views?\s+and\s+tables?)\b|"
    r"describe\s+(the\s+)?schema|"
    r"explain\s+(the\s+)?schema|"
    r"show\s+(the\s+)?schema|"
    r"schema\s+overview|"
    r"database\s+schema|"
    r"table\s+catalog|"
    r"data\s+dictionary|"
    r"all\s+tables?\s+and\s+views?"
    r")\b",
    re.IGNORECASE,
)

_METADATA_PATTERNS = re.compile(
    r"\b("
    r"what\s+tables?\s+exist|list\s+(the\s+)?tables?|show\s+(the\s+)?tables?|"
    r"list\s+(the\s+)?(views?|columns?)|show\s+(the\s+)?(views?|columns?)|"
    r"describe\s+(the\s+)?(table|view)\b|"
    r"row\s+counts?|primary\s+keys?|foreign\s+keys?|relationships?|"
    r"sample\s+rows?|show\s+sample|preview\s+rows?|"
    r"what\s+columns?|columns?\s+(for|of|in)\b|"
    r"information_schema|sys\.tables"
    r")\b",
    re.IGNORECASE,
)


def is_understanding_question(question: str) -> bool:
    lower = question.lower().strip()
    return any(phrase in lower for phrase in _BUSINESS_UNDERSTANDING_PHRASES)


def is_schema_question(question: str) -> bool:
    return bool(_SCHEMA_PATTERNS.search(question or ""))


def is_reasoning_question(question: str) -> bool:
    return bool(_REASONING_PATTERNS.search(question or ""))


def is_factual_kpi_question(question: str) -> bool:
    """True only for numeric KPI asks, not yield/failure reasoning."""
    if is_reasoning_question(question):
        return False
    return bool(_KPI_PATTERNS.search(question or ""))


def classify_intent(question: str) -> QuestionIntent:
    """
    Classify WHAT the user is asking before routing or SQL generation.

    Order: Smalltalk → Knowledge → Reasoning → KPI → Business understanding →
    Schema → Metadata → Analytical.
    """
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    if _SMALLTALK.match(cleaned):
        return QuestionIntent.SMALLTALK

    if _KNOWLEDGE_PATTERNS.search(cleaned):
        return QuestionIntent.KNOWLEDGE

    # Reasoning before KPI so "what influences yield" is not treated as a metric fetch
    if is_reasoning_question(cleaned):
        return QuestionIntent.BUSINESS_REASONING

    if is_factual_kpi_question(cleaned):
        return QuestionIntent.KPI

    if is_understanding_question(cleaned):
        return QuestionIntent.BUSINESS_UNDERSTANDING

    if is_schema_question(cleaned):
        return QuestionIntent.SCHEMA

    if _METADATA_PATTERNS.search(cleaned):
        return QuestionIntent.METADATA

    return QuestionIntent.ANALYTICAL


def is_kpi_question(question: str) -> bool:
    return classify_intent(question) == QuestionIntent.KPI
