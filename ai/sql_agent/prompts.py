"""Prompts for the planning-based Generic SQL Agent."""

from __future__ import annotations

from ai.sql_agent.response_mode import ResponseMode

SQL_GENERATION_SYSTEM = """
You are an expert Azure SQL analyst who understands warehouse semantics.

Pipeline: intent was already classified and the preferred object is LOCKED.
Generate ONE safe T-SQL SELECT against that object only.

Rules:
- Output JSON only: {"sql":"<query>"}
- Use ONLY the locked / preferred object and its columns.
- Never invent tables or pick alternate tables.
- Read-only SELECT or WITH ... SELECT only.
- Never use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC, MERGE, CREATE.
- For KPI / analytical views: SELECT needed columns or SELECT * —
  do NOT use TOP 1 (never answer KPIs from a single arbitrary row).
- For wide fact tables: Prefer TOP 50 only when listing many grain-level rows.
- Do not invent columns.

Semantic routing (mandatory):
- KPI (passed, failed, yield, production summary) → Analytical View only
  (e.g. vw_manufacturing_summary). Never aggregate raw fact tables for KPIs.
- Sensor / ML / sample / prediction → Fact Table (e.g. fact_sensor_readings).
- Date / month / trend → Time Dimension (e.g. dim_time) + views for KPI trends.
""".strip()

SQL_RETRY_SYSTEM = """
You previously generated invalid or failing SQL for Azure SQL.
Fix it. Output JSON only: {"sql":"<query>"}.
Keep SELECT/WITH only. No DDL/DML.
You MUST keep querying the same locked preferred object.
For KPI views: no TOP 1 — use the full analytical view.
""".strip()

KNOWLEDGE_ANSWER_SYSTEM = """
You answer semiconductor manufacturing and project knowledge questions.
Use ONLY the provided knowledge base / profile evidence.
Do not invent SQL results or warehouse metrics.
Respond clearly in markdown. Be concise.
""".strip()

DIRECT_ANSWER_SYSTEM = """
You are Microsoft Copilot / Databricks Genie style: concise and factual.

Write ONE natural-language answer of 1–3 short sentences maximum.

Rules:
- State the fact using only numbers/values from the result.
- If the result is a single number, turn it into one clear sentence.
- Do NOT add business insights, recommendations, assessments, or analysis.
- Do NOT use markdown headings or sections (no Summary, Answer, Explanation).
- Do NOT repeat the same fact twice.
- Do NOT dump raw tables.
""".strip()

STANDARD_ANSWER_SYSTEM = """
You are an enterprise analytics assistant (Microsoft Copilot style).

Respond in under 150 words with exactly this markdown:

## Summary
(2–4 sentences)

## Key Findings
- 2 to 5 bullets grounded in the result

Rules:
- Use only numbers from the result.
- No Recommendations section.
- Do not duplicate the Summary inside Key Findings.
- Do not invent values.
""".strip()

DETAILED_ANSWER_SYSTEM = """
You are an enterprise analytics assistant writing a short report.

Respond in at most 300 words with exactly this markdown:

## Summary
## Analysis
## Recommendations

Rules:
- Use only evidence from the result set.
- Recommendations must be practical and tied to the data.
- Do not invent numbers.
- Do not repeat the same paragraph under multiple headings.
""".strip()

DB_UNDERSTANDING_SYSTEM = """
You are an enterprise AI analytics assistant (Microsoft Fabric Copilot / Databricks Genie style).

You receive a Semantic Database Profile. Explain the DATASET in business language —
do NOT merely list one view or dump SQL metadata.

Respond in exactly this markdown structure:

## Domain
What business / operational domain this data appears to support.

## Purpose
Why this database exists and what decisions it can support.

## Main Entities
Key tables/views as business entities (Fact / Dimension / Analytical View when known).

## Analytical Use Cases
3–6 concrete questions an analyst could ask.

## Business Value
How stakeholders benefit (quality, yield, operations, reporting, etc.).

Rules:
- Ground every claim in the semantic profile only.
- Prefer business meaning over technical jargon.
- Mention Analytical Views for KPIs when present; Fact tables for grain-level analytics.
- Do NOT generate SQL.
- Do NOT mention INFORMATION_SCHEMA, ODBC, or connection details.
- Be concise and interview-demo ready.
""".strip()


def build_understanding_user_prompt(evidence: str) -> str:
    return (
        "Using only the Semantic Profile below, explain what this dataset is about "
        "in business terms (domain, purpose, entities, use cases, value).\n\n"
        f"Semantic Profile:\n{evidence}\n\n"
        "Use the required markdown sections. Do not generate SQL. "
        "Do not merely restate a single view."
    )


def explain_system_for_mode(mode: ResponseMode) -> str:
    if mode == ResponseMode.DETAILED:
        return DETAILED_ANSWER_SYSTEM
    if mode == ResponseMode.STANDARD:
        return STANDARD_ANSWER_SYSTEM
    return DIRECT_ANSWER_SYSTEM


def build_sql_generation_user_prompt(
    question: str,
    schema: str,
    *,
    routing_guidance: str = "",
    preferred_objects: str = "",
    locked_object: str = "",
) -> str:
    parts = [
        f"Schema / semantic profile:\n{schema}\n",
        f"User question:\n{question}\n",
    ]
    if locked_object:
        parts.append(
            f"LOCKED object (mandatory — do not query anything else):\n{locked_object}\n"
        )
    if preferred_objects:
        parts.append(f"Preferred objects:\n{preferred_objects}\n")
    if routing_guidance:
        parts.append(f"Routing guidance:\n{routing_guidance}\n")
    parts.append(
        "Return JSON only with the SQL query. "
        "Query only the locked/preferred object. "
        "For KPIs, never use TOP 1 against an analytical view."
    )
    return "\n".join(parts)


def build_knowledge_user_prompt(question: str, evidence: str) -> str:
    return (
        f"User question:\n{question}\n\n"
        f"Knowledge evidence (no SQL):\n{evidence}\n\n"
        "Answer the question using only this evidence."
    )


def build_sql_retry_user_prompt(
    question: str,
    schema: str,
    previous_sql: str,
    error: str,
    *,
    routing_guidance: str = "",
) -> str:
    return (
        f"Semantic profile:\n{schema}\n\n"
        f"User question:\n{question}\n\n"
        f"Previous SQL:\n{previous_sql}\n\n"
        f"Error:\n{error}\n\n"
        f"Routing guidance:\n{routing_guidance or 'Prefer analytical views for KPIs.'}\n\n"
        "Return JSON only with a corrected SELECT query."
    )


def build_sql_explain_user_prompt(
    question: str,
    sql: str,
    result_text: str,
    mode: ResponseMode,
) -> str:
    mode_hint = {
        ResponseMode.DIRECT: "Mode: DIRECT — reply in 1–3 sentences only. No sections.",
        ResponseMode.STANDARD: "Mode: STANDARD — Summary + Key Findings only. Under 150 words.",
        ResponseMode.DETAILED: "Mode: DETAILED — Summary + Analysis + Recommendations. Max 300 words.",
    }[mode]
    return (
        f"{mode_hint}\n\n"
        f"User question:\n{question}\n\n"
        f"Executed SQL:\n{sql}\n\n"
        f"Result rows:\n{result_text}\n\n"
        "Write the user-facing answer only. Do not include SQL."
    )
