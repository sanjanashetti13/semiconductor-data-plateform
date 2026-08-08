# Architecture

## System Flow

```text
User
  ↓
React (AI Workspace)
  ↓
FastAPI
  ↓
AI Router / SQL Agent
  ↓
Tools
  ↓
Azure SQL
  ↑
Databricks ETL (Bronze → Silver → Gold)

Power BI ──(separate)──→ Azure SQL
```

## Mode 1 — Manufacturing Copilot
1. User asks a natural-language question.
2. Router selects `knowledge` or a SQL analytics tool.
3. Tool returns evidence (knowledge base or Azure SQL query results).
4. Groq LLM formats a business report (Summary, Key Metrics, Assessment, Actions).

## Mode 2 — Generic SQL Agent
1. User connects Azure SQL credentials (session memory).
2. Backend inspects `INFORMATION_SCHEMA.TABLES` / `COLUMNS`.
3. LLM receives **schema only**, generates one SELECT.
4. Validator rejects mutating / dangerous SQL.
5. Query executes; LLM explains the result set.

## Key Components
| Component | Responsibility |
| --- | --- |
| `ai/tools/*` | Manufacturing analytics + knowledge tools |
| `ai/sql_agent/*` | Session store, schema inspect, validate, NL→SQL |
| `backend/routers/copilot.py` | Manufacturing copilot API |
| `backend/routers/sql_agent.py` | Generic SQL agent API |
| `frontend/src/pages/*` | Copilot, Connect, SQL Agent, Power BI, About, Architecture |
