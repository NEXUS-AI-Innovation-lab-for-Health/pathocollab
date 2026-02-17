#!/bin/bash
set -euo pipefail

# ====== CONFIG DB (Postgres) ======
DB_CONTAINER="pixtral-postgres"     # <- nom du container postgres
DB_USER="pixtral_user"      # <- user postgres
DB_NAME="auth_db"           # <- nom de la base

# ====== CONFIG API ======
API_URL="http://localhost:8000/api/auth/register"

echo "Suppression des users (table users)..."
docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" <<'SQL'
BEGIN;
-- Si d'autres tables référencent users, TRUNCATE CASCADE est pratique
TRUNCATE TABLE users RESTART IDENTITY CASCADE;
COMMIT;
SQL

create_user () {
    local email="$1"
    local password="$2"
    local full_name="$3"
    local role="$4"

    echo "👤 Création: $email ($role)"
    curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{
        \"email\": \"$email\",
        \"password\": \"$password\",
        \"full_name\": \"$full_name\",
        \"role\": \"$role\"
        }"
    echo
}

echo "🔄 Recréation des users via l'API..."
# Mots de passe >= 8 caractères (contrainte UserCreate)
create_user "admin@gmail.com"  "adminadmin"   "Admin"        "admin"
create_user "arthur@gmail.com" "arthur1234"   "Dr. Arthur"   "anatomopathologiste"
create_user "louna@gmail.com"  "louna1234"    "Dr. Louna"    "anatomopathologiste"
create_user "jack@gmail.com"   "jack1234"     "Dr. Jack"     "oncologue"

echo "✅ Terminé."
echo "📋 Vérification DB:"
docker exec -it "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT email, full_name, role, is_active, is_verified, created_at FROM users ORDER BY created_at DESC;"
