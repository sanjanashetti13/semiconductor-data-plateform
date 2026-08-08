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
pip install -r backend/requirements.txt
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
| `GROQ_API_KEY` | Yes | LLM access |
| `GROQ_MODEL` | No | Default `llama-3.3-70b-versatile` |
| `AZURE_SQL_SERVER` | Mode 1 only | Curated manufacturing warehouse |
| `AZURE_SQL_DATABASE` | Mode 1 only | Warehouse database name |
| `AZURE_SQL_USERNAME` | Mode 1 only | SQL login |
| `AZURE_SQL_PASSWORD` | Mode 1 only | SQL password |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `VITE_API_BASE_URL` | No | Frontend API base (empty = same origin / proxy) |
| `VITE_POWERBI_URL` | No | Optional default Power BI URL (still overridable in UI) |

**Security rules**

- No secrets in frontend JavaScript except non-sensitive public URLs
- Generic Mode passwords are **never** written to disk; they live in server memory for the active session only
- Browser may remember Server / Database / Username (not password)

---

## Deployment Guide

### Vercel (UI + API)

This monorepo deploys on Vercel as:

1. **Static UI** — `frontend` built into `public/`
2. **FastAPI** — `backend.main:app` for `/api/*`

`pyproject.toml` sets `entrypoint = "backend.main:app"`.  
`scripts/vercel_build.sh` builds the React app into `public/`.

**Required Vercel env vars**

- `GROQ_API_KEY`
- `CORS_ORIGINS` — include `https://your-app.vercel.app` (or `*`)

**Azure SQL on Vercel**

Vercel’s Python runtime does **not** include Microsoft ODBC drivers.  
Database Connection will return a clear 503 on that host.

For full Azure SQL:

- Run API on **Azure App Service / Render / Railway** with `backend/requirements.txt` (includes `pyodbc`), **or**
- Run `uvicorn` locally and point `VITE_API_BASE_URL` at that API

### Docker Compose (local / VM)

```bash
cp .env.example .env
# set GROQ_API_KEY and optional AZURE_SQL_*
docker compose up --build
```

### Azure App Service / Render / Railway (API)

- Deploy the Python API (`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`)
- Set env vars in the host secret store (`GROQ_API_KEY`, `CORS_ORIGINS`, optional `AZURE_SQL_*`)
- Do **not** bake `.env` into the image

### Vercel / Static host (frontend)

- Build `frontend` with `VITE_API_BASE_URL` pointing at your API
- Never put `GROQ_API_KEY` or SQL passwords in `VITE_*` variables

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
