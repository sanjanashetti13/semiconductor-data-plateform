"""Intent classification — WHAT the user is asking (before table routing / SQL)."""

from __future__ import annotations

import re
from enum import Enum


class QuestionIntent(str, Enum):
    """Primary question intents for the enterprise SQL analytics assistant."""

    KPI = "kpi"
    METADATA = "metadata"
    SCHEMA = "schema"
    BUSINESS_UNDERSTANDING = "business_understanding"
    ANALYTICAL = "analytical"
    KNOWLEDGE = "knowledge"
    SMALLTALK = "smalltalk"


_SMALLTALK = re.compile(
    r"^(hi|hello|hey|hiya|good\s+(morning|afternoon|evening)|thanks|thank\s+you|"
    r"ok|okay|yo|sup)[\s!.?]*$",
    re.IGNORECASE,
)

# Domain / conceptual — never SQL (generic + semiconductor)
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

# Business meaning of the connected dataset (profile → narrative, no SQL gen)
_BUSINESS_UNDERSTANDING_PHRASES = (
    "what does this database contain",
    "what does the database contain",
    "what is the dataset about",
    "what is this dataset about",
    "what's the dataset about",
    "what is this data about",
    "what is the data about",
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
    "what can i analyze",
    "what insights can i get",
)

# Schema / catalog structure
_SCHEMA_PATTERNS = re.compile(
    r"\b("
    r"explain\s+(every|all|each)\s+tables?|"
    r"explain\s+tables?|"
    r"describe\s+(every|all|each)\s+tables?|"
    r"what\s+does\s+each\s+table\s+contain|"
    r"describe\s+(the\s+)?schema|"
    r"explain\s+(the\s+)?schema|"
    r"show\s+(the\s+)?schema|"
    r"schema\s+overview|"
    r"database\s+schema|"
    r"table\s+catalog|"
    r"data\s+dictionary"
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


def classify_intent(question: str) -> QuestionIntent:
    """
    Classify WHAT the user is asking before routing or SQL generation.

    Order: Smalltalk → Knowledge → KPI → Business understanding → Schema →
    Metadata → Analytical.
    """
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("Question cannot be empty.")

    if _SMALLTALK.match(cleaned):
        return QuestionIntent.SMALLTALK

    if _KNOWLEDGE_PATTERNS.search(cleaned):
        return QuestionIntent.KNOWLEDGE

    if _KPI_PATTERNS.search(cleaned):
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
