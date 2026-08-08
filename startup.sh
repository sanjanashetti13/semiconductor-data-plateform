#!/usr/bin/env bash
# Azure App Service (Linux) startup — no Docker.
# Configure App Service → Configuration → General settings → Startup Command:
#   bash startup.sh
#
# Or set Startup Command directly to:
#   python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

set -euo pipefail

cd "$(dirname "$0")"

export APP_ENV="${APP_ENV:-production}"
PORT="${PORT:-8000}"

echo "Starting Semiconductor Intelligence Hub on 0.0.0.0:${PORT}"

# ODBC Driver 18 must already be present on the App Service image / custom startup.
# This script does not install system packages (no Docker / no apt by default).

if [[ ! -f "frontend/dist/index.html" && ! -f "public/index.html" && ! -f "backend/static/index.html" ]]; then
  echo "WARNING: React build not found (frontend/dist). Run npm run build during deploy."
fi

exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
