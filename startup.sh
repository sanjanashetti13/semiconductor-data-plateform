#!/usr/bin/env bash
# Azure App Service (Linux) startup — no Docker.
#
# App Service → Configuration → General settings → Startup Command:
#   bash startup.sh
#
# Equivalent direct command:
#   python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

set -euo pipefail

cd "$(dirname "$0")"

export APP_ENV="${APP_ENV:-production}"
PORT="${PORT:-8000}"

# Activate Oryx / App Service virtualenv when present (created during deploy).
if [[ -f "antenv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source antenv/bin/activate
elif [[ -f "/antenv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source /antenv/bin/activate
elif [[ -n "${VIRTUAL_ENV:-}" && -f "${VIRTUAL_ENV}/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${VIRTUAL_ENV}/bin/activate"
fi

echo "Starting Semiconductor Intelligence Hub on 0.0.0.0:${PORT} (APP_ENV=${APP_ENV})"

# ODBC Driver 18 must be available on the App Service image.
# This script does not install system packages and never hardcodes driver paths.
# If ODBC is missing, the API still starts; Azure SQL routes return a safe 503.

if [[ ! -f "frontend/dist/index.html" && ! -f "public/index.html" && ! -f "backend/static/index.html" ]]; then
  echo "WARNING: React build not found (frontend/dist). Ensure the CI build step ran npm run build."
fi

exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT"
