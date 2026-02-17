#!/bin/bash
set -e

echo "Initializing Pixtral databases..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ROOT_DIR="$(pwd)"
COMPOSE_CMD="docker-compose -f infra/docker-compose.dev.yml"

# 1) Vérifier que le conteneur PostgreSQL tourne
if ! $COMPOSE_CMD ps postgres | grep -q "Up"; then
    echo -e "${YELLOW}PostgreSQL container is not running. Start it with:${NC}"
    echo -e "${YELLOW}  docker-compose -f infra/docker-compose.dev.yml up -d postgres${NC}"
    exit 1
fi

echo -e "${GREEN}PostgreSQL container is running, waiting for it to be ready...${NC}"

# Attendre que Postgres soit prêt
until $COMPOSE_CMD exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -e "${YELLOW}PostgreSQL not ready yet, retrying in 2 seconds...${NC}"
    sleep 2
done

echo -e "${GREEN}PostgreSQL is ready!${NC}"

# 2) Lancer les migrations pour chaque service
services=("auth-service" "cases-service" "workflow-service" "images-service" "reports-service")

for service in "${services[@]}"; do
    echo -e "\n${GREEN}Running migrations for $service...${NC}"

    SERVICE_DIR="$ROOT_DIR/apps/$service"
    VENV_DIR="$SERVICE_DIR/venv"

    if [ ! -d "$SERVICE_DIR" ]; then
        echo -e "${YELLOW}Directory $SERVICE_DIR not found, skipping.${NC}"
        continue
    fi

    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${YELLOW}Virtualenv not found for $service in $VENV_DIR${NC}"
        echo -e "${YELLOW}Run: ./scripts/install_python_services.sh${NC}"
        continue
    fi

    cd "$SERVICE_DIR"

    # Activer le venv du service
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"

    # Vérifier qu'il y a bien une config Alembic
    if [ ! -f "alembic.ini" ] || [ ! -f "alembic/env.py" ]; then
        echo -e "${YELLOW}No Alembic configuration found for $service (missing alembic.ini or alembic/env.py). Skipping migrations for this service.${NC}"
        deactivate
        cd "$ROOT_DIR"
        continue
    fi

    # Créer le dossier des migrations s'il n'existe pas
    mkdir -p alembic/versions

    # Créer une migration initiale s'il n'y en a pas
    if [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
        echo "Creating initial migration..."
        alembic revision --autogenerate -m "Initial migration"
    fi

    # Lancer les migrations
    alembic upgrade head

    # Désactiver le venv
    deactivate

    cd "$ROOT_DIR"
done


echo -e "\n${GREEN}All databases initialized successfully!${NC}"
