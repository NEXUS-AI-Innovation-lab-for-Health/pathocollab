#!/usr/bin/env sh
set -eu

: "${SERVICE_HOST:=0.0.0.0}"
: "${SERVICE_PORT:=8003}"

# IMPORTANT: en docker, jamais localhost. On vise le service "postgres".
: "${DATABASE_URL:=postgresql+asyncpg://pixtral_user:pixtral_pass@postgres:5432/workflow_db}"

export DATABASE_URL

echo "🔎 workflow-service starting..."
echo "   DATABASE_URL=${DATABASE_URL}"
echo "   Listening on ${SERVICE_HOST}:${SERVICE_PORT}"

# --- Wait Postgres ---
DB_HOST="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\1#p')"
DB_PORT="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\2#p')"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"

echo "⏳ Waiting for postgres at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 60); do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
    echo "✅ Postgres is ready"
    break
  fi
  sleep 1
done

# --- Migrations Alembic ---
if [ -f "alembic.ini" ]; then
  echo "🗄️  Running migrations: alembic upgrade head"
  alembic upgrade head
else
  echo "⚠️  alembic.ini not found, skipping migrations"
fi

# --- Start API ---
echo "🚀 Starting Uvicorn"
exec uvicorn app.main:app --host "$SERVICE_HOST" --port "$SERVICE_PORT"