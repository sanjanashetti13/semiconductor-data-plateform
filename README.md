# Semiconductor Intelligence Hub

Enterprise AI Data Analytics Platform for semiconductor manufacturing intelligence **and** a generic AI SQL agent for any Azure SQL database.

## Two Modes

### Mode 1 — Semiconductor Manufacturing Intelligence
Azure Databricks (Bronze → Silver → Gold) → Azure SQL → Power BI + AI Manufacturing Copilot  
Ask project and business questions about wafers, yield, sensors, ETL, and architecture.

### Mode 2 — Generic AI SQL Agent
Connect any Azure SQL database → inspect `INFORMATION_SCHEMA` → natural language → validated `SELECT` → explain results.

## Features
- Knowledge tool (no SQL) for project / domain education
- Modular SQL analytics tools for curated SECOM gold data
- Safe SELECT-only SQL agent for arbitrary Azure SQL schemas
- ChatGPT-style React workspace
- Power BI configuration (external dashboard link)
- Docker + cloud deployment ready

## Quick Start

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -r backend/requirements.txt
cp .env.example .env

uvicorn backend.main:app --reload --port 8000

cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173/copilot

## Documentation
- [Architecture](docs/Architecture.md)
- [Deployment](docs/Deployment.md)
- [API](docs/API.md)
- [Folder Structure](docs/FolderStructure.md)

## Security
- Passwords for the SQL Agent are stored in **server memory** for the session only
- Passwords are **never logged** and not persisted to disk by the agent flow
- Only validated `SELECT` / `WITH ... SELECT` statements are executed

## License
MIT
