#!/usr/bin/env sh
set -eu

: "${SERVICE_HOST:=0.0.0.0}"
: "${SERVICE_PORT:=8003}"
: "${DATABASE_URL:=postgresql+asyncpg://pixtral_user:pixtral_pass@postgres:5432/workflow_db}"

export DATABASE_URL

DB_HOST="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\1#p')"
DB_PORT="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\2#p')"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"

SYNC_DB_URL="$(echo "$DATABASE_URL" | sed 's#postgresql+asyncpg://#postgresql://#')"
export ALEMBIC_DATABASE_URL="$SYNC_DB_URL"

echo "🔎 workflow-service starting..."
echo "   DATABASE_URL=${DATABASE_URL}"
echo "   Listening on ${SERVICE_HOST}:${SERVICE_PORT}"

echo "⏳ Waiting for postgres (real connection) ..."
for i in $(seq 1 60); do
  if PGPASSWORD="${POSTGRES_PASSWORD:-pixtral_pass}" \
      psql "$SYNC_DB_URL" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Postgres accepts SQL connections"
    break
  fi
  sleep 1
done

if [ -f "alembic.ini" ]; then
  echo "🗄️  Running migrations: alembic upgrade head"
  alembic upgrade head
fi

echo "🚀 Starting Uvicorn"
exec uvicorn app.main:app --host "$SERVICE_HOST" --port "$SERVICE_PORT"
