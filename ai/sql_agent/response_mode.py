"""Intent-based response length modes (Copilot / Genie style)."""

from __future__ import annotations

import re
from enum import Enum


class ResponseMode(str, Enum):
    DIRECT = "direct"  # 1–3 sentences, default for factual asks
    STANDARD = "standard"  # Summary + Key Findings, <150 words
    DETAILED = "detailed"  # Summary + Analysis + Recommendations, ≤300 words


_DETAILED_PATTERNS = re.compile(
    r"\b("
    r"explain|analyze|analyse|analysis|why\b|root\s+cause|full\s+report|"
    r"recommendations?|recommend|detailed|in\s+detail|deep\s+dive|"
    r"comprehensive|thorough"
    r")\b",
    re.IGNORECASE,
)

_STANDARD_PATTERNS = re.compile(
    r"\b("
    r"overall\s+(production\s+)?summary|monthly\s+yield|compare|comparison|"
    r"best\s+month|worst\s+month|trend|breakdown|by\s+month|over\s+time|"
    r"production\s+summary|sensor\s+comparison|versus|vs\.?"
    r")\b",
    re.IGNORECASE,
)

# Strong factual / scalar cues → Direct (default)
_DIRECT_PATTERNS = re.compile(
    r"\b("
    r"how\s+many|what\s+is\s+the|what'?s\s+the|count|total|percentage|percent|"
    r"yield|failed|passes?|pass\s+rate|fail\s+rate|row\s+counts?|"
    r"list\s+the|show\s+me\s+the\s+number|number\s+of"
    r")\b",
    re.IGNORECASE,
)


def classify_response_mode(question: str) -> ResponseMode:
    """
    Choose answer length from the user question.

    Detailed only when explicitly requested. Standard for known analytical asks.
    Everything else defaults to Direct (simple factual).
    """
    cleaned = question.strip()
    if not cleaned:
        return ResponseMode.DIRECT

    if _DETAILED_PATTERNS.search(cleaned):
        return ResponseMode.DETAILED

    if _STANDARD_PATTERNS.search(cleaned):
        return ResponseMode.STANDARD

    if _DIRECT_PATTERNS.search(cleaned):
        return ResponseMode.DIRECT

    # Short questions default to direct; longer open asks → standard
    if len(cleaned.split()) <= 12:
        return ResponseMode.DIRECT

    return ResponseMode.STANDARD
