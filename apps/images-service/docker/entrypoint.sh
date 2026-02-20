#!/usr/bin/env sh
set -eu

# Defaults (override in docker-compose)
: "${SERVICE_HOST:=0.0.0.0}"
: "${SERVICE_PORT:=8004}"

: "${DATABASE_URL:=postgresql+asyncpg://pixtral_user:pixtral_pass@postgres:5432/images_db}"

: "${MINIO_ENDPOINT:=http://minio:9000}"
: "${MINIO_ACCESS_KEY:=minioadmin}"
: "${MINIO_SECRET_KEY:=minioadmin}"

# Buckets attendus (optionnel)
: "${MINIO_BUCKET_IMAGES:=pixtral-images}"
: "${MINIO_BUCKET_WSI:=pixtral-wsi-images}"

export DATABASE_URL
export MINIO_ENDPOINT MINIO_ACCESS_KEY MINIO_SECRET_KEY
export MINIO_BUCKET_IMAGES MINIO_BUCKET_WSI

echo "🔎 images-service starting..."
echo "   DATABASE_URL=${DATABASE_URL}"
echo "   MINIO_ENDPOINT=${MINIO_ENDPOINT}"
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

# --- Wait MinIO ---
# (MinIO répond sur /minio/health/ready)
MINIO_READY_URL="${MINIO_ENDPOINT%/}/minio/health/ready"
echo "⏳ Waiting for MinIO at ${MINIO_READY_URL}..."
for i in $(seq 1 60); do
  if curl -fsS "$MINIO_READY_URL" >/dev/null 2>&1; then
    echo "✅ MinIO is ready"
    break
  fi
  sleep 1
done

# --- Migrations Alembic (si présent) ---
if [ -f "alembic.ini" ]; then
  echo "🗄️  Running migrations: alembic upgrade head"
  alembic upgrade head
else
  echo "⚠️  alembic.ini not found, skipping migrations"
fi

# --- Start API ---
echo "🚀 Starting Uvicorn"
exec uvicorn app.main:app --host "$SERVICE_HOST" --port "$SERVICE_PORT"