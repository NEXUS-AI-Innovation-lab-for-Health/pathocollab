#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")"/.. && pwd)"

PORTS=(8000 8001 8002 8003 8004 3000)

echo "=============================="
echo "   START STACK ONCO NEXCODE   "
echo "=============================="

# --- PRE-CLEAN : libère les ports (uvicorn / node) ---
echo ""
echo "[PRE-CLEAN] Libération des ports: ${PORTS[*]}"
for p in "${PORTS[@]}"; do
  # récupère les PID qui écoutent sur le port
  PIDS=$(lsof -ti tcp:"$p" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "${PIDS}" ]]; then
    echo " - Port $p occupé par PID(s): $PIDS -> kill -TERM"
    kill -TERM $PIDS 2>/dev/null || true
    sleep 1
    # si ça résiste, kill -9
    PIDS2=$(lsof -ti tcp:"$p" -sTCP:LISTEN 2>/dev/null || true)
    if [[ -n "${PIDS2}" ]]; then
      echo "   Port $p toujours occupé -> kill -KILL $PIDS2"
      kill -KILL $PIDS2 2>/dev/null || true
    fi
  else
    echo " - Port $p libre"
  fi
done

# --- INFRA ---
gnome-terminal --title="INFRA" -- bash -c "
cd \"$BASE_DIR/infra\";
docker-compose -f docker-compose.dev.yml up -d;
echo 'Infra lancée';
exec bash
"

sleep 5

# --- BACKEND ---
gnome-terminal --title="BACKEND" -- bash -c "
cd \"$BASE_DIR/backend\";
source venv/bin/activate;
uvicorn server:app --host 0.0.0.0 --port 8000 --reload;
exec bash
"

# --- AUTH ---
gnome-terminal --title="AUTH-SERVICE" -- bash -c "
cd \"$BASE_DIR/apps/auth-service\";
source venv/bin/activate;
uvicorn app.main:app --port 8001 --reload;
exec bash
"

# --- CASES ---
gnome-terminal --title="CASES-SERVICE" -- bash -c "
cd \"$BASE_DIR/apps/cases-service\";
source venv/bin/activate;
uvicorn app.main:app --port 8002 --reload;
exec bash
"

# --- WORKFLOW ---
gnome-terminal --title="WORKFLOW-SERVICE" -- bash -c "
cd \"$BASE_DIR/apps/workflow-service\";
source venv/bin/activate;
uvicorn app.main:app --port 8003 --reload;
exec bash
"

# --- REPORTS ---
gnome-terminal --title="REPORTS-SERVICE" -- bash -c "
cd \"$BASE_DIR/apps/reports-service\";
source venv/bin/activate;
uvicorn app.main:app --port 8004 --reload;
exec bash
"

sleep 3

# --- FRONTEND ---
gnome-terminal --title="FRONTEND" -- bash -c "
cd \"$BASE_DIR/frontend\";
npm start;
exec bash
"
