# 🚀 Quick Start Guide - Pixtral Platform

Guide de démarrage rapide en 5 minutes.

## 💻 Prérequis (installer une fois)

```bash
# Vérifier les installations
docker --version          # Docker >= 24.0
docker-compose --version  # Docker Compose >= 2.20
node --version            # Node.js >= 20.0
python --version          # Python >= 3.11
yarn --version            # Yarn >= 1.22
```

Si manquant : [Guide d'installation complet](./DEPLOYMENT.md#prérequis)

---

## ⚡ Installation express (3 commandes)

### 1. Cloner et installer

```bash
git clone <repo-url>
cd pixtral-platform
yarn install
```

### 2. Démarrer l'infrastructure

```bash
cd infra
docker-compose -f docker-compose.dev.yml up -d
cd ..
sleep 30  # Attendre que PostgreSQL démarre
```

### 3. Initialiser et lancer

```bash
# Installer les dépendances Python
for service in auth-service cases-service workflow-service images-service reports-service; do
    cd apps/$service && pip install -r requirements.txt && cd ../..
done

# Migrations DB
chmod +x scripts/*.sh
bash scripts/init-databases.sh

# Démarrer tous les services
bash scripts/start-all-services.sh
```

**C'est prêt !** 🎉

Ouvrez http://localhost:3000

---

## 🔧 Commandes utiles

### Services

```bash
# Démarrer tout
bash scripts/start-all-services.sh

# Arrêter tout
bash scripts/stop-all-services.sh

# Voir les logs
tail -f logs/auth-service.log
tail -f logs/web.log

# Healthchecks
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

### Base de données

```bash
# Se connecter à PostgreSQL
psql -h localhost -U pixtral_user -d auth_db

# Créer une migration
cd apps/auth-service
alembic revision --autogenerate -m "My change"

# Appliquer les migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Tests

```bash
# Backend tests
cd apps/auth-service
pytest --cov=app

# Frontend tests
cd apps/web
yarn test

# Lint
ruff check apps/auth-service/app/
yarn lint
```

---

## 🎯 URLs rapides

| Service | URL | Login |
|---------|-----|-------|
| 🖥️ **App Web** | http://localhost:3000 | Créer compte |
| 📄 API Docs | http://localhost:8001/docs | - |
| 📊 Grafana | http://localhost:3001 | admin / pixtral2025 |
| 📦 MinIO | http://localhost:9001 | minioadmin / minioadmin |
| 🔌 n8n | http://localhost:5678 | admin / pixtral2025 |

---

## 👨‍💻 Créer votre premier utilisateur

### Via API

```bash
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dr.dupont@hospital.fr",
    "password": "SecurePass123!",
    "full_name": "Dr. Marie Dupont",
    "role": "anatomopathologiste"
  }'
```

### Via Interface Web

1. Ouvrir http://localhost:3000
2. Cliquer sur "Créer un compte" (si implémenté)
3. Remplir le formulaire
4. Se connecter

---

## 🐛 Dépannage express

### Service ne démarre pas

```bash
# Vérifier les logs
docker-compose -f infra/docker-compose.dev.yml logs postgres
tail -f logs/auth-service.log

# Redémarrer un service
pkill -f "uvicorn.*8001"
cd apps/auth-service && uvicorn app.main:app --port 8001 --reload
```

### Port déjà utilisé

```bash
# Trouver le processus
lsof -ti:8001

# Tuer le processus
kill -9 $(lsof -ti:8001)
```

### Base de données ne répond pas

```bash
# Redémarrer PostgreSQL
cd infra
docker-compose -f docker-compose.dev.yml restart postgres

# Tester la connexion
psql -h localhost -U pixtral_user -d auth_db -c "SELECT 1;"
```

### Réinitialiser complètement

⚠️ **Attention : Supprime toutes les données**

```bash
bash scripts/stop-all-services.sh
cd infra
docker-compose -f docker-compose.dev.yml down -v
cd ..
rm -rf logs/*
bash scripts/start-all-services.sh
```

---

## 📚 Documentation complète

- [README.md](./README.md) : Vue d'ensemble
- [ARCHITECTURE.md](./ARCHITECTURE.md) : Architecture détaillée
- [DEPLOYMENT.md](./DEPLOYMENT.md) : Guide de déploiement
- [CONTRIBUTING.md](./CONTRIBUTING.md) : Guide de contribution
- [User Stories PDF](./Projet%206%20SAE%20UserStories.pdf) : Spécifications

---

## ❓ Besoin d'aide ?

1. Vérifier la [documentation](./README.md)
2. Consulter les [Issues GitHub](https://github.com/org/pixtral/issues)
3. Contacter l'équipe

Bonne chance ! 🚀
