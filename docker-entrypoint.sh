#!/bin/sh
set -e

# Ensure data dirs exist (in case persistent volume is empty on first boot)
mkdir -p /app/data/public /app/data/private /app/data/reports /app/data/cache/diagnosis

# Seed the DB idempotently (no-op if already seeded)
cd /app/apps/api
python -m app.seed || echo "Seed already applied or skipped."

# Start the server — Railway sets PORT, default 8000
exec uvicorn app.main:app \
    --app-dir /app/apps/api \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1
