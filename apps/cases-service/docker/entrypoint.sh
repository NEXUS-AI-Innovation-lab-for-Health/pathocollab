#!/usr/bin/env sh
set -eu

# Valeurs par défaut (surchargées via docker-compose environment)
: "${SERVICE_HOST:=0.0.0.0}"
: "${SERVICE_PORT:=8002}"
: "${DATABASE_URL:=postgresql+asyncpg://pixtral_user:pixtral_pass@postgres:5432/cases_db}"

export DATABASE_URL

echo "🔎 cases-service starting..."
echo "   DATABASE_URL=${DATABASE_URL}"
echo "   Listening on ${SERVICE_HOST}:${SERVICE_PORT}"

# Attendre Postgres (simple et efficace)
# On extrait host/port depuis DATABASE_URL si possible, sinon fallback.
DB_HOST="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\1#p')"
DB_PORT="$(echo "$DATABASE_URL" | sed -n 's#.*@\(.*\):\([0-9]\+\)/.*#\2#p')"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"

echo "⏳ Waiting for postgres (real connection) ..."
for i in $(seq 1 60); do
  if PGPASSWORD="${POSTGRES_PASSWORD:-pixtral_pass}" \
      psql "postgresql://pixtral_user@${DB_HOST}:${DB_PORT}/cases_db" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Postgres accepts SQL connections"
    break
  fi
  sleep 1
done

# Lancer les migrations Alembic
if [ -f "alembic.ini" ]; then
  echo "🗄️  Running migrations: alembic upgrade head"
  alembic upgrade head
else
  echo "⚠️  alembic.ini not found, skipping migrations"
fi

# Démarrer l'API
echo "🚀 Starting Uvicorn"
exec uvicorn app.main:app --host "$SERVICE_HOST" --port "$SERVICE_PORT"