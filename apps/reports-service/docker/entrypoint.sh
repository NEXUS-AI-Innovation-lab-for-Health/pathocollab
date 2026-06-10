#!/usr/bin/env sh
set -eu

: "${SERVICE_HOST:=0.0.0.0}"
: "${SERVICE_PORT:=8005}"

# En docker: jamais localhost
: "${DATABASE_URL:=postgresql+asyncpg://pixtral_user:pixtral_pass@postgres:5432/reports_db}"

# Optionnel : si tu utilises Qdrant dans ce service
: "${QDRANT_URL:=http://qdrant:6333}"
: "${WAIT_FOR_QDRANT:=false}"

export DATABASE_URL QDRANT_URL

echo "🔎 reports-service starting..."
echo "   DATABASE_URL=${DATABASE_URL}"
echo "   QDRANT_URL=${QDRANT_URL}"
echo "   Listening on ${SERVICE_HOST}:${SERVICE_PORT}"

# --- Wait Postgres ---
DB_HOST="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\1#p')"
DB_PORT="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\2#p')"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"

echo "⏳ Waiting for postgres (real connection) ..."
for i in $(seq 1 60); do
  if PGPASSWORD="${POSTGRES_PASSWORD:-pixtral_pass}" \
      psql "postgresql://pixtral_user@${DB_HOST}:${DB_PORT}/reports_db" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Postgres accepts SQL connections"
    break
  fi
  sleep 1
done

# --- Wait Qdrant (optionnel) ---
if [ "${WAIT_FOR_QDRANT}" = "true" ]; then
  QDRANT_HEALTH="${QDRANT_URL%/}/healthz"
  echo "⏳ Checking Qdrant at ${QDRANT_HEALTH}..."

  QDRANT_WAIT_SECONDS="${QDRANT_WAIT_SECONDS:-10}"

  for i in $(seq 1 "$QDRANT_WAIT_SECONDS"); do
    if curl -fsS "$QDRANT_HEALTH" >/dev/null 2>&1; then
      echo "✅ Qdrant is ready"
      break
    fi

    if [ "$i" = "$QDRANT_WAIT_SECONDS" ]; then
      echo "⚠️ Qdrant not ready. Starting reports-service anyway."
    fi

    sleep 1
  done
fi

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