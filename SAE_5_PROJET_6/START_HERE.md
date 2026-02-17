# 🚀 START HERE - Pixtral Platform

## Bienvenue sur Pixtral !

Ce fichier vous guide pour démarrer rapidement la plateforme.

---

## 📝 Ce qu'il faut savoir

### Qu'est-ce que Pixtral ?

Pixtral est une **plateforme collaborative médicale** pour l'analyse de biopsies entre anatomopathologistes et oncologues, avec **assistance IA (GPT-4o)**.

### Architecture

- **5 microservices backend** (FastAPI + PostgreSQL)
- **1 frontend React** moderne
- **8 composants d'infrastructure** (Redis, MinIO, Kafka, Qdrant, etc.)
- **CI/CD GitHub Actions** complet
- **Monitoring Prometheus + Grafana**

---

## ⚡ Démarrage Ultra-Rapide (5 min)

### 1️⃣ Vérifier les prérequis

```bash
docker --version       # >= 24.0
node --version         # >= 20.0
python --version       # >= 3.11
yarn --version         # >= 1.22
```

❌ **Manquant ?** → Voir [DEPLOYMENT.md](./DEPLOYMENT.md)

---

### 2️⃣ Démarrer l'infrastructure

```bash
cd infra
docker-compose -f docker-compose.dev.yml up -d
cd ..
```

⏳ **Attendre 30 secondes** que PostgreSQL soit prêt.

---

### 3️⃣ Installer les dépendances

```bash
# Root (Turborepo)
yarn install

# Backend (5 services)
for service in auth-service cases-service workflow-service images-service reports-service; do
    cd apps/$service && pip install -r requirements.txt && cd ../..
done

# Frontend
cd apps/web && yarn install && cd ../..
```

---

### 4️⃣ Initialiser les bases de données

```bash
chmod +x scripts/*.sh
bash scripts/init-databases.sh
```

---

### 5️⃣ Démarrer les services

```bash
bash scripts/start-all-services.sh
```

⏳ **Attendre 30 secondes** que tout démarre.

---

### 6️⃣ Créer des données de démo

```bash
bash scripts/seed-demo-data.sh
```

---

### 7️⃣ Accéder à l'application

🔗 **Ouvrir** : http://localhost:3000

🔐 **Se connecter avec** :
- **Email** : `louna.dubois@pixtral.fr`
- **Password** : `Louna123!`

---

## 🎯 URLs Importantes

| Service | URL | Credentials |
|---------|-----|-------------|
| 🖥️ **App Web** | http://localhost:3000 | louna.dubois@pixtral.fr / Louna123! |
| 📄 API Docs Auth | http://localhost:8001/docs | - |
| 📄 API Docs Cases | http://localhost:8002/docs | - |
| 📄 API Docs Workflow | http://localhost:8003/docs | - |
| 📄 API Docs Images | http://localhost:8004/docs | - |
| 📄 API Docs Reports | http://localhost:8005/docs | - |
| 📊 **Grafana** | http://localhost:3001 | admin / pixtral2025 |
| 📦 **MinIO** | http://localhost:9001 | minioadmin / minioadmin |
| 🔌 **n8n** | http://localhost:5678 | admin / pixtral2025 |

---

## 🔍 Tester l'Installation

### Healthchecks

```bash
curl http://localhost:8001/health  # Auth
curl http://localhost:8002/health  # Cases
curl http://localhost:8003/health  # Workflow
curl http://localhost:8004/health  # Images
curl http://localhost:8005/health  # Reports
```

### Créer un utilisateur via API

```bash
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "full_name": "Dr. Test",
    "role": "anatomopathologiste"
  }'
```

---

## 🚽 Arrêter les Services

```bash
bash scripts/stop-all-services.sh
```

---

## 🐛 Problèmes ?

### Port déjà utilisé

```bash
# Trouver et tuer le processus
lsof -ti:8001
kill -9 $(lsof -ti:8001)
```

### PostgreSQL ne répond pas

```bash
cd infra
docker-compose -f docker-compose.dev.yml restart postgres
```

### Réinitialiser complètement

```bash
bash scripts/stop-all-services.sh
cd infra
docker-compose -f docker-compose.dev.yml down -v
cd ..
bash scripts/start-all-services.sh
```

---

## 📚 Documentation Complète

| Fichier | Description |
|---------|-------------|
| [README.md](./README.md) | Vue d'ensemble et quick start |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Architecture détaillée |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Guide de déploiement |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Guide de contribution |
| [QUICK_START.md](./QUICK_START.md) | Guide rapide |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | État du projet |
| [FINAL_SUMMARY.md](./FINAL_SUMMARY.md) | Résumé de livraison |

---

## 🛠️ Commandes Utiles

### Logs

```bash
tail -f logs/auth-service.log
tail -f logs/web.log
```

### Tests

```bash
bash scripts/run-tests.sh
```

### Migrations

```bash
cd apps/auth-service
alembic revision --autogenerate -m "My change"
alembic upgrade head
```

---

## ✨ Fonctionnalités Principales

- ✅ Authentification JWT
- ✅ Gestion de cas patients
- ✅ Workflow collaboratif tour-par-tour
- ✅ Upload et gestion d'images WSI
- ✅ **Assistance IA GPT-4o** pour rapports
- ✅ Notifications temps réel
- ✅ Monitoring Grafana

---

## 👥 Utilisateurs de Démo

Après `seed-demo-data.sh` :

| Utilisateur | Email | Password | Rôle |
|-------------|-------|----------|------|
| Admin | admin@pixtral.fr | Admin123! | admin |
| Dr. Louna Dubois | louna.dubois@pixtral.fr | Louna123! | anatomopathologiste |
| Dr. Arthur Laurent | arthur.laurent@pixtral.fr | Arthur123! | anatomopathologiste |
| Dr. Léa Roux | lea.roux@pixtral.fr | Lea123! | oncologue |

---

## ❓ Questions ?

1. Lire la [documentation](./README.md)
2. Consulter [DEPLOYMENT.md](./DEPLOYMENT.md)
3. Vérifier [PROJECT_STATUS.md](./PROJECT_STATUS.md)

---

**Bonne découverte de Pixtral !** 🎉
