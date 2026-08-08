"""Knowledge tool — domain and project Q&A without SQL."""

from __future__ import annotations

KNOWLEDGE_BASE = """
# Semiconductor Intelligence Hub — Knowledge Base

## Project
Semiconductor Intelligence Hub is an enterprise AI Manufacturing Copilot for
semiconductor production analytics. It combines Azure Databricks ETL, Azure SQL,
Power BI dashboards, and a Groq-powered AI router with modular analytics tools.

Users ask natural-language questions. The AI router selects either this knowledge
tool or a SQL analytics tool. SQL tools never invent numbers; they query the warehouse.

## SECOM Dataset
SECOM (Semiconductor Manufacturing) is a public UCI dataset of wafer process sensor
readings used for fault detection and yield analysis.
- Each row is typically one wafer / production observation.
- Features are anonymized sensor measurements from the process line.
- The classification target indicates pass vs fail outcome.
- In this platform, curated gold data is loaded into Azure SQL table
  `fact_sensor_readings` for analytics.

## Semiconductor Manufacturing Basics
Semiconductor manufacturing fabricates integrated circuits on silicon wafers through
many process steps (deposition, etch, lithography, metrology, test).
High-dimensional sensor telemetry monitors equipment health and process stability.
Small drifts can increase defectivity and reduce yield.

## Wafers
A wafer is a thin slice of semiconductor material that holds many dies.
Yield is driven by how many wafers/dies meet quality criteria after processing and test.

## Sensors
Sensors capture process signals (temperature, pressure, flow, electrical signatures, etc.).
In SECOM, sensor columns are numbered (for example sensor_160, sensor_162).
Comparing sensor averages for pass vs fail wafers can highlight process signals linked
to failures.

## Pass / Fail
In this warehouse:
- target = -1 typically means PASS
- target = 1 typically means FAIL
Pass/fail outcomes are used to compute yield and sensor comparisons.

## Yield
Yield percentage ≈ (passed wafers / total wafers) × 100.
Higher yield means better process quality and lower scrap cost.
Monthly yield trends help identify best/worst production periods.

## Azure SQL
Azure SQL Database stores the curated gold-layer fact table used by the AI tools
and Power BI. The AI SQL tools query `fact_sensor_readings` through secure ODBC.

## Azure Databricks
Databricks runs the Bronze → Silver → Gold medallion ETL (PySpark) that cleans and
curates manufacturing sensor data before loading into Azure SQL.

### Bronze
Raw ingested sensor / SECOM data with minimal transformation. Preserves source fidelity.

### Silver
Cleaned and standardized data: typed columns, null handling, basic quality rules.

### Gold
Analytics-ready curated facts (for example `fact_sensor_readings`) consumed by
Azure SQL tools, Power BI, and the AI Manufacturing Copilot.

### ETL Pipeline
1. Ingest SECOM / manufacturing extracts into Bronze.
2. Clean and conform into Silver.
3. Publish Gold metrics into Azure SQL.
4. Serve insights via Power BI and the AI Copilot.

## Dual Product Modes
1. Semiconductor Manufacturing Intelligence — domain copilot over the curated warehouse.
2. Generic AI SQL Agent — connect any Azure SQL database, inspect schema, generate
   safe SELECT queries, and explain results.

## Power BI
Power BI connects to Azure SQL for executive dashboards (yield, defects, sensors).
The web app does not recreate Power BI; it links out to the published dashboard.

## Architecture
Azure Databricks (Bronze → Silver → Gold)
  → Azure SQL Database
  → Power BI (dashboards) and FastAPI AI Copilot (conversational analytics)
  → React AI Workspace UI

## AI Copilot Tools
SQL analytics tools: overall_summary, monthly_yield, sensor_comparison,
best_month, worst_month, recommendations.
Knowledge tool: answers conceptual/project questions without querying SQL.
""".strip()


def run(question: str | None = None) -> dict:
    """
    Return project/domain knowledge for the LLM to answer conceptual questions.

    No Azure SQL access. Optional ``question`` is echoed for prompt grounding.
    """
    payload = KNOWLEDGE_BASE
    if question and question.strip():
        payload = f"User question focus:\n{question.strip()}\n\n{KNOWLEDGE_BASE}"

    return {
        "tool": "knowledge",
        "columns": [],
        "rows": [],
        "data": payload,
        "data_source": "Project Knowledge Base",
    }
