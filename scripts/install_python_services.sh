#!/usr/bin/env bash
set -e

# Script pour créer un venv et installer les dépendances
# pour tous les services Python du projet.

SERVICES=("auth-service" "cases-service" "workflow-service" "images-service" "reports-service")

ROOT_DIR="$(pwd)"

echo "📁 Répertoire du projet : $ROOT_DIR"
echo "🧪 Vérification de python3..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 n'est pas installé. Installe-le avec : sudo apt install -y python3 python3-venv python3-pip"
  exit 1
fi

for SERVICE in "${SERVICES[@]}"; do
  SERVICE_DIR="$ROOT_DIR/apps/$SERVICE"

  echo "------------------------------"
  echo "➡️  Service : $SERVICE"
  echo "📂 Dossier : $SERVICE_DIR"

  if [ ! -d "$SERVICE_DIR" ]; then
    echo "⚠️  Dossier $SERVICE_DIR introuvable, je passe au suivant."
    continue
  fi

  cd "$SERVICE_DIR"

  # Nom du venv
  VENV_DIR="$SERVICE_DIR/venv"

  echo "🐍 Création de l'environnement virtuel : $VENV_DIR"
  python3 -m venv "$VENV_DIR"

  echo "✅ Activation du venv..."
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"

  echo "⬆️ Mise à jour de pip..."
  pip install --upgrade pip

  if [ -f "requirements.txt" ]; then
    echo "📦 Installation des dépendances depuis requirements.txt..."
    pip install -r requirements.txt
  else
    echo "⚠️ Aucun requirements.txt trouvé dans $SERVICE_DIR"
  fi

  echo "🚪 Désactivation du venv pour $SERVICE"
  deactivate

  cd "$ROOT_DIR"
done

echo "✅ Installation terminée pour tous les services Python."
echo "ℹ️ Pour lancer un service, par ex auth-service :"
echo "   cd apps/auth-service && source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
