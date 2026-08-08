"""Intent-based response length modes (Copilot / Genie style)."""

from __future__ import annotations

import re
from enum import Enum


class ResponseMode(str, Enum):
    DIRECT = "direct"  # one concise sentence / 1–3 sentences
    STANDARD = "standard"  # short structured explanation
    DETAILED = "detailed"  # summary + recommendations


_DETAILED_PATTERNS = re.compile(
    r"\b("
    r"explain|analyze|analyse|analysis|why\b|root\s+cause|full\s+report|"
    r"recommendations?|recommend|detailed|in\s+detail|deep\s+dive|"
    r"comprehensive|thorough|influence|affect|reduce\s+failures?|"
    r"improve\s+yield|factors?|opportunit"
    r")\b",
    re.IGNORECASE,
)

_STANDARD_PATTERNS = re.compile(
    r"\b("
    r"overall\s+(production\s+)?summary|monthly\s+yield|compare|comparison|"
    r"best\s+month|worst\s+month|trend|breakdown|by\s+month|over\s+time|"
    r"production\s+summary|sensor\s+comparison|versus|vs\.?|"
    r"what\s+is\s+this\s+(dataset|database)|used\s+for|overview|"
    r"explain\s+(every|all|each)\s+tables?|what\s+objects?"
    r")\b",
    re.IGNORECASE,
)

_DIRECT_PATTERNS = re.compile(
    r"\b("
    r"how\s+many|what\s+is\s+the\s+overall\s+yield|count|total\s+wafers?|"
    r"passed|failed|pass\s+rate|fail\s+rate|row\s+counts?|"
    r"number\s+of"
    r")\b",
    re.IGNORECASE,
)


def classify_response_mode(question: str) -> ResponseMode:
    """
    Simple factual → Direct (one sentence)
    Business / catalog → Standard (structured)
    Deep analytical / reasoning → Detailed (summary + recommendations)
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

    if len(cleaned.split()) <= 10:
        return ResponseMode.DIRECT

    return ResponseMode.STANDARD
