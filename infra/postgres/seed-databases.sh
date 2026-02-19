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

run_sql "auth_db"     "/docker-entrypoint-initdb.d/seed/auth.sql"
run_sql "cases_db"    "/docker-entrypoint-initdb.d/seed/cases.sql"
run_sql "workflow_db" "/docker-entrypoint-initdb.d/seed/workflow.sql"
run_sql "images_db"   "/docker-entrypoint-initdb.d/seed/images.sql"
run_sql "reports_db"  "/docker-entrypoint-initdb.d/seed/reports.sql"

echo "Seeding done."
