#!/bin/bash
set -euo pipefail

echo "Seeding databases..."

run_sql () {
    local db="$1"
    local file="$2"
    if [ -f "$file" ]; then
        echo "  -> Seeding $db with $file"
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" -f "$file"
    else
        echo "  -> Skip (missing): $file"
    fi
}

run_sql "auth_db"     "/docker-entrypoint-initdb.d/seed/10-auth.sql"
run_sql "cases_db"    "/docker-entrypoint-initdb.d/seed/20-cases.sql"
run_sql "workflow_db" "/docker-entrypoint-initdb.d/seed/30-workflow.sql"
run_sql "images_db"   "/docker-entrypoint-initdb.d/seed/40-images.sql"
run_sql "reports_db"  "/docker-entrypoint-initdb.d/seed/50-reports.sql"

echo "Seeding done."
