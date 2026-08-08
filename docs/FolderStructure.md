# Folder Structure

```text
semiconductor-data-platform/
├── ai/
│   ├── config.py
│   ├── database.py              # Curated manufacturing warehouse access
│   ├── llm.py
│   ├── prompt.py
│   ├── router.py
│   ├── copilot.py
│   ├── tools/                   # Knowledge + SQL analytics tools
│   └── sql_agent/               # Generic NL→SQL agent
│       ├── agent.py
│       ├── prompts.py
│       ├── session_store.py
│       └── validator.py
├── backend/
│   ├── main.py
│   ├── schemas.py
│   └── routers/
│       ├── copilot.py
│       └── sql_agent.py
├── frontend/
│   └── src/
│       ├── pages/               # Copilot, Connect, SQL Agent, Power BI, About, Architecture
│       ├── components/
│       └── services/api.ts
├── docs/
│   ├── Architecture.md
│   ├── Deployment.md
│   ├── API.md
│   └── FolderStructure.md
├── etl/                         # Databricks / PySpark helpers
├── Dockerfile
├── docker-compose.yml
└── README.md
```
