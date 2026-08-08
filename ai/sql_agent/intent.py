"""Intent classification — WHAT the user is asking (before table routing / SQL)."""

from __future__ import annotations

import re
from enum import Enum


class QuestionIntent(str, Enum):
    """Primary question intents for the Generic SQL Agent."""

    KPI = "kpi"
    METADATA = "metadata"
    ANALYTICAL = "analytical"
    KNOWLEDGE = "knowledge"
    SMALLTALK = "smalltalk"


_SMALLTALK = re.compile(
    r"^(hi|hello|hey|hiya|good\s+(morning|afternoon|evening)|thanks|thank\s+you|"
    r"ok|okay|yo|sup)[\s!.?]*$",
    re.IGNORECASE,
)

# Domain / conceptual — never SQL
_KNOWLEDGE_PATTERNS = re.compile(
    r"\b("
    r"what\s+is\s+(the\s+)?secom(\s+dataset)?|"
    r"what\s+is\s+a\s+wafer|"
    r"what\s+(are|is)\s+(a\s+)?(wafer|sensor|yield|die|fab)|"
    r"explain\s+(semiconductor|wafer|secom|manufacturing|etl|bronze|silver|gold)|"
    r"what\s+is\s+semiconductor\s+manufacturing|"
    r"how\s+does\s+(semiconductor|wafer|yield)|"
    r"tell\s+me\s+about\s+(secom|wafers?|sensors?|semiconductor\s+manufacturing)|"
    r"what\s+does\s+(a\s+)?(sensor|wafer)\s+(measure|mean)|"
    r"project\s+knowledge|knowledge\s+base|"
    r"what\s+is\s+(bronze|silver|gold)\s+layer|"
    r"medallion\s+architecture"
    r")\b",
    re.IGNORECASE,
)

# Business KPIs — must use analytical views / aggregated totals
_KPI_PATTERNS = re.compile(
    r"\b("
    r"how\s+many\s+(passed|failed|pass|fail|wafers?)(\s+wafers?)?|"
    r"number\s+of\s+(passed|failed|pass|fail|wafers?)|"
    r"passed(\s+wafers?)?|failed(\s+wafers?)?|"
    r"pass\s+(rate|percentage|percent|%)|"
    r"fail(ure)?\s+(rate|percentage|percent|%)|"
    r"overall\s+yield|yield\s*(%|percentage|percent|rate)?|"
    r"total\s+wafers?|total\s+production|overall\s+production|"
    r"production\s+summary|manufacturing\s+summary|"
    r"overall\s+(production\s+)?summary|"
    r"\bkpi\b|throughput|quality\s+rate|defect\s+rate"
    r")\b",
    re.IGNORECASE,
)

# Schema / catalog — profile or metadata templates, not analytical SQL
_METADATA_PATTERNS = re.compile(
    r"\b("
    r"what\s+tables?\s+exist|list\s+(the\s+)?tables?|show\s+(the\s+)?tables?|"
    r"list\s+(the\s+)?(views?|columns?)|show\s+(the\s+)?(views?|columns?)|"
    r"describe\s+(the\s+)?(schema|database|dataset|table|view)|"
    r"explain\s+(this\s+|the\s+)?(schema|database|dataset)|"
    r"what\s+does\s+(this\s+|the\s+)?database\s+contain|"
    r"summarize\s+(this\s+|the\s+)?(database|schema|dataset)|"
    r"database\s+overview|schema\s+overview|"
    r"row\s+counts?|primary\s+keys?|foreign\s+keys?|relationships?|"
    r"sample\s+rows?|show\s+sample|preview\s+rows?|"
    r"what\s+columns?|columns?\s+(for|of|in)\b|"
    r"information_schema|sys\.tables"
    r")\b",
    re.IGNORECASE,
)

# Explicit database-understanding phrases (subset of metadata, profile-only path)
_UNDERSTANDING_PHRASES = (
    "what does this database contain",
    "what does the database contain",
    "what is the dataset about",
    "what is this dataset about",
    "what's the dataset about",
    "what is this data about",
    "summarize what this database",
    "summarize this database",
    "summarize the database",
    "summarize this schema",
    "explain this schema",
    "explain this database",
    "explain the database",
    "explain this dataset",
    "database overview",
    "what's in this database",
    "what is in this database",
    "describe this database",
    "describe the database",
    "describe this dataset",
    "tell me about this database",
    "tell me about this dataset",
)


def is_understanding_question(question: str) -> bool:
    lower = question.lower().strip()
    return any(phrase in lower for phrase in _UNDERSTANDING_PHRASES)


def classify_intent(question: str) -> QuestionIntent:
    """
    Classify WHAT the user is asking before routing or SQL generation.

    Order: Smalltalk → Knowledge → KPI → Metadata → Analytical (default).
    """
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    if _SMALLTALK.match(cleaned):
        return QuestionIntent.SMALLTALK

    if _KNOWLEDGE_PATTERNS.search(cleaned):
        return QuestionIntent.KNOWLEDGE

    # KPI before metadata so "yield" / "how many passed" never become catalog asks
    if _KPI_PATTERNS.search(cleaned):
        return QuestionIntent.KPI

    if is_understanding_question(cleaned) or _METADATA_PATTERNS.search(cleaned):
        return QuestionIntent.METADATA

    return QuestionIntent.ANALYTICAL


def is_kpi_question(question: str) -> bool:
    return classify_intent(question) == QuestionIntent.KPI
