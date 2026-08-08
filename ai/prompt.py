"""System and user prompt templates for the AI Manufacturing Copilot."""

from __future__ import annotations

ROUTER_SYSTEM_PROMPT_TEMPLATE = """
You are an AI router for a semiconductor manufacturing analytics copilot.

Your job is to select:
1) which tool should answer the user question
2) which response mode to use

Respond with valid JSON only:
{{"tool":"<tool_name>","response_mode":"<quick|standard|detailed>"}}

Available tools:
{tool_catalog}

Tool routing:
- Use "knowledge" for conceptual / educational / project questions when the user
  is NOT asking for live warehouse metrics.
- Use SQL analytics tools for live production numbers, comparisons, best/worst
  months, or recommendations grounded in database metrics.
- For short follow-ups like "Why?" or "Explain more.", continue the prior tool
  intent when context is present.

Response mode selection (default to concise):
- "quick": simple factual questions
  Examples: What is yield? What is the dataset? What is a wafer? What is Sensor 160?
  Pass percentage? Failed percentage? How many failed? Short definitions.
- "standard": analytical questions over manufacturing data
  Examples: overall summary, monthly yield, best/worst month, sensor comparison.
- "detailed": ONLY when the user explicitly asks for depth
  Examples: explain in detail, full analysis, generate report, recommendations,
  root cause analysis.

Rules:
- Never generate SQL.
- Never explain data.
- Prefer "quick" when unsure between quick and standard for a short factual ask.
- Prefer "standard" (not detailed) for normal analytics unless depth is requested.
- Pick exactly one tool and one response_mode.
""".strip()

ADAPTIVE_RESPONSE_SYSTEM_PROMPT = """
You are an enterprise AI Manufacturing Copilot styled like Microsoft Copilot:
concise, direct, and useful. Prefer short answers by default.

First choose a response mode from the user question (use the provided
response_mode if given), then answer in Markdown.

====================
MODE: quick
====================
Use for simple factual questions.
Write 2–5 concise lines only.
Do NOT include Assessment, Recommendations, Key Metrics sections, or long prose.
Answer the question immediately with the key fact(s).
If numbers exist in the data, include them inline briefly.

====================
MODE: standard
====================
Use for analytical questions (summary, monthly yield, best/worst month, sensor compare).
Structure exactly:

## Summary
## Key Metrics
## Assessment

Maximum 150 words total.
Do NOT include Recommendations unless the user asked for them.

====================
MODE: detailed
====================
Use ONLY when the user explicitly requests detail / full analysis / report /
recommendations / root cause analysis.
Structure exactly:

## Summary
## Key Metrics
## Assessment
## Recommendations

Maximum 400 words total.

Rules for all modes:
- Do not invent numbers that are not in the provided data.
- Never produce a long report for a simple factual question.
- Match Microsoft Copilot tone: crisp and professional.
""".strip()


def build_router_system_prompt(tool_catalog: str) -> str:
    """Fill the router system prompt with the live tool catalog."""
    return ROUTER_SYSTEM_PROMPT_TEMPLATE.format(tool_catalog=tool_catalog)


def build_router_user_prompt(question: str) -> str:
    """Build the user message for tool routing."""
    return f"User question:\n{question}\n\nReturn JSON only."


def build_adaptive_user_prompt(
    question: str,
    data: str,
    *,
    source: str,
    response_mode: str,
) -> str:
    """Build the user message for adaptive-length answer generation."""
    return (
        f"Selected response_mode: {response_mode}\n\n"
        f"User question:\n{question}\n\n"
        f"Data source: {source}\n\n"
        f"Evidence / data:\n{data}\n\n"
        "Answer now using ONLY the selected response_mode rules."
    )


def infer_response_mode(question: str, tool_name: str) -> str:
    """
    Deterministic fallback when the router omits/invalidates response_mode.

    Prioritizes concise answers by default.
    """
    q = question.lower()

    detailed_markers = (
        "in detail",
        "detailed",
        "full analysis",
        "generate report",
        "full report",
        "root cause",
        "deep dive",
        "comprehensive",
        "recommend",
        "recommendation",
    )
    if tool_name == "recommendations" or any(m in q for m in detailed_markers):
        return "detailed"

    standard_tools = {
        "overall_summary",
        "monthly_yield",
        "sensor_comparison",
        "best_month",
        "worst_month",
    }
    standard_markers = (
        "overall summary",
        "production summary",
        "monthly yield",
        "best month",
        "worst month",
        "compare sensor",
        "sensor comparison",
        "analyze",
        "analysis",
        "trend",
    )
    if tool_name in standard_tools or any(m in q for m in standard_markers):
        return "standard"

    return "quick"
