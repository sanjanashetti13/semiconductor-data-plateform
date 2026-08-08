# Deployment Guide

## Local Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:8080  
- Backend: http://localhost:8000/docs  

Provide a `.env` with Azure SQL and `GROQ_API_KEY`.

## Frontend (Vercel / Netlify / Azure Static Web Apps)
1. Set root to `frontend/`
2. Build command: `npm run build`
3. Output: `dist`
4. Env:
   - `VITE_API_BASE_URL=https://<your-api-host>`
   - `VITE_POWERBI_URL=` (optional)
   - `VITE_GITHUB_URL=` (optional)

## Backend (Render / Railway / Azure App Service)
1. Deploy from repo root using `Dockerfile`
2. Start command alternative: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Required env:
   - `SQL_SERVER`, `SQL_DATABASE`, `SQL_USERNAME`, `SQL_PASSWORD`
   - `GROQ_API_KEY`, `GROQ_MODEL`
   - `CORS_ORIGINS=https://your-frontend-domain`

## Notes
- ODBC Driver 18 for SQL Server must be available on the backend host (included in Dockerfile).
- SQL Agent sessions are in-memory — multi-instance backends need sticky sessions or shared session store for production HA.
