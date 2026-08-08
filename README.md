# Azure Data Copilot / Semiconductor Intelligence Hub

Enterprise AI analytics platform for semiconductor manufacturing intelligence **and** a generic Azure SQL Copilot for any database.

Suitable for demos, technical interviews, and deployment on Azure App Service, Render, Railway, or a Vite frontend + Python API.

---

## Project Overview

Users connect an Azure SQL database, ask natural-language questions, and receive business-ready answers. The platform:

1. Profiles schema semantics (tables, views, keys, roles)
2. Classifies intent (KPI · Schema · Business reasoning · Analytical · Knowledge)
3. Executes **read-only** SQL only when needed
4. Reasons over the full schema for “what is this database used for?” style questions

**Semiconductor Mode** activates automatically when curated objects are present (`fact_sensor_readings`, `dim_time`, `vw_manufacturing_summary`).

**Generic SQL Mode** activates for any other Azure SQL database.

---

## Architecture

```
React (Vite)  →  FastAPI  →  Groq LLM
                    ↓
              Azure SQL (session credentials or .env for Mode 1)
                    ↓
              Power BI (external URL, browser-local)
```

| Layer | Responsibility |
|--------|----------------|
| Frontend | Copilot chat, Database Connection, Power BI link, Architecture |
| Backend | Intent routing, schema profiling, KPI aggregation, safe SQL |
| Azure SQL | Warehouse / any customer database |
| Groq | Natural-language generation & SQL drafting |
| Power BI | External executive dashboards (not recreated in-app) |

---

## Technology Stack

- **Frontend:** React, TypeScript, Vite, Tailwind
- **Backend:** FastAPI, Python 3.11+
- **Data:** Azure SQL Database (ODBC Driver 18)
- **AI:** Groq (`llama-3.3-70b-versatile` by default)
- **BI:** Power BI (configured URL opens externally)
- **Optional ETL:** Azure Databricks medallion (Bronze → Silver → Gold)

---

## How to Run

### Prerequisites

- Python 3.11+
- Node.js 20+
- ODBC Driver 18 for SQL Server
- Groq API key
- Azure SQL database (for Copilot)

### Backend

```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
# Optional local ETL stack: pip install -r requirements-etl.txt
cp .env.example .env
# Edit .env — at minimum set GROQ_API_KEY

uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://127.0.0.1:5173/copilot

1. Go to **Database Connection**
2. Enter Azure SQL Server, Database, Username, Password
3. Connect, then ask questions in **AI Copilot**

---

## Environment Variables

Copy `.env.example` → `.env`. **Never commit `.env`.**

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | LLM access (backend only) |
| `GROQ_MODEL` | No | Default `llama-3.3-70b-versatile` |
| `SQL_SERVER` / `AZURE_SQL_SERVER` | Mode 1 | Curated warehouse host |
| `SQL_DATABASE` / `AZURE_SQL_DATABASE` | Mode 1 | Database name |
| `SQL_USERNAME` / `AZURE_SQL_USERNAME` | Mode 1 | SQL login |
| `SQL_PASSWORD` / `AZURE_SQL_PASSWORD` | Mode 1 | SQL password |
| `CORS_ORIGINS` | No | Dev localhost list; leave empty for same-origin production |
| `POWERBI_URL` | No | Ops hint only — users configure URL in the UI |
| `VITE_API_BASE_URL` | No | Leave empty for same-origin `/api` |
| `VITE_POWERBI_URL` | No | Optional public default Power BI URL (no secrets) |

**Security rules**

- Never put `GROQ_API_KEY` or SQL credentials in `VITE_*` variables
- Generic Mode passwords are **never** written to disk; server memory for the active session only
- Browser may remember Server / Database / Username (not password)
- Production API responses never include stack traces or raw ODBC/SQL Server errors

---

## Deployment Guide

### Azure App Service (recommended — one URL, no Docker)

```
Browser → https://<app-name>.azurewebsites.net
              ├── /api/*   → FastAPI (Groq, Azure SQL via pyodbc)
              └── /*       → React (frontend/dist)
```

**Local production smoke test**

```bash
cd frontend && npm ci && npm run build && cd ..
# Windows PowerShell
$env:APP_ENV="production"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- UI: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/api/health` → `{"status":"healthy"}`

**App Service**

| Setting | Value |
|---------|--------|
| OS | Linux |
| Stack | Python 3.11+ |
| Startup Command | `bash startup.sh` or `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |

Build the frontend during deploy (`cd frontend && npm ci && npm run build`) so `frontend/dist/index.html` exists on the worker.

**Required App Settings:** `GROQ_API_KEY`, `APP_ENV=production`, and for Semiconductor Mode `SQL_SERVER`, `SQL_DATABASE`, `SQL_USERNAME`, `SQL_PASSWORD`.

**ODBC Driver 18:** logged at startup. Optional operator endpoint `/api/diagnostics/odbc` when `ENABLE_DIAGNOSTICS=true` (disable afterward).

### Local development (two processes)

Vite on `:5173` proxies `/api` → FastAPI on `:8000`. See **How to Run** above.

### Optional: Vercel / Docker

See `docs/Deployment.md`. Vercel Python runtimes do not include ODBC Driver 18.

---

## Azure SQL Configuration

1. Create an Azure SQL Database and firewall rule for your client / App Service outbound IPs
2. Create a least-privilege read login for demos when possible
3. For Generic Mode: enter credentials on **Database Connection**
4. For Semiconductor Mode: load gold data (optional script uses env vars only):

```bash
# Requires AZURE_SQL_* in .env and data/gold_sensor_data.csv
python scripts/load_gold_to_sql.py
```

On connect, the API profiles tables/views/columns/keys once and caches the schema until Disconnect.

---

## Power BI Configuration

1. Open **Power BI** in the app
2. Click **Configure Dashboard**
3. Paste a Report URL or Embed URL
4. Stored in **this browser only** (localStorage) — never committed to git

---

## AI Workflow

```
Question
  → Intent classification (KPI | Schema | Business | Analytical | Knowledge | Reasoning)
  → Semantic routing (Semiconductor locks vs generic profile)
  → SQL only when factual data is required (SELECT validated)
  → Business narrative for reasoning / whole-database questions
  → Dynamic follow-up suggestions
```

Developer Mode (Settings gear, **OFF by default**) reveals SQL, routing, model, and timing.

---

## Folder Structure

```
backend/           FastAPI app + routers
ai/                Copilot, SQL agent, tools, LLM
ai/sql_agent/      Planner, profiler, KPI, semantics, validator
frontend/          React workspace
scripts/           Ops scripts (env-based; no hardcoded secrets)
docs/              Extra architecture / API notes
tests/             Pytest suites
data/              Sample / gold data (large files gitignored where configured)
.env.example       Template — copy to .env
```

---

## Screenshots

Add screenshots under `docs/screenshots/` (optional):

- `copilot.png` — AI Copilot chat
- `database-connection.png` — Azure SQL connect form
- `power-bi.png` — Power BI configure dialog
- `architecture.png` — Platform architecture page

---

## Security Checklist

- [x] No hardcoded Azure SQL passwords or Groq keys in source
- [x] `.env` gitignored
- [x] SELECT-only SQL validation (DROP/DELETE/UPDATE/INSERT/ALTER/CREATE/TRUNCATE/EXEC/MERGE rejected)
- [x] Friendly user errors; detailed failures logged server-side
- [x] Session credentials cleared on Disconnect
- [x] Developer Mode hidden / off by default

If a password was ever committed historically, **rotate it in Azure** immediately.

---

## Future Enhancements

- Persistent multi-user auth (Entra ID)
- Row-level security / governed semantic models
- Streaming token responses
- Automated CI security scanning
- Managed Power BI embed tokens (service principal)

---

## License

MIT
