# Guide de Déploiement Pixtral

## Prérequis

### Logiciels requis
- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **Node.js** >= 20.0
- **Python** >= 3.11
- **PostgreSQL Client** (psql)
- **Git**

### Clés API
- **EMERGENT_LLM_KEY** : Déjà configurée dans les .env
- **JWT_SECRET_KEY** : Générer une clé sécurisée pour production

## Installation locale (Développement)

### 1. Cloner le repository
```bash
git clone <repo-url>
cd pathocollab
```

### 2. Installer les dépendances
```bash
# Root (Turborepo)
yarn install

# Backend services
for service in auth-service cases-service workflow-service images-service reports-service; do
    cd apps/$service
    pip install -r requirements.txt
    cd ../..
done

# Frontend
cd apps/web
yarn install
cd ../..
```

### 3. Démarrer l'infrastructure
```bash
cd infra
docker-compose -f docker-compose.dev.yml up -d
```

Cela démarre :
- PostgreSQL (5 bases de données)
- Redis
- MinIO
- Redpanda (Kafka)
- Qdrant
- n8n
- Prometheus + Grafana

### 4. Initialiser les bases de données
```bash
cd ..
chmod +x scripts/*.sh
bash scripts/init-databases.sh
```

### 5. Démarrer les services

#### Option A : Script automatique
```bash
bash scripts/start-all-services.sh
```

#### Option B : Manuel
```bash
# Terminal 1 - Auth Service
cd apps/auth-service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 - Cases Service
cd apps/cases-service
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3 - Workflow Service
cd apps/workflow-service
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

# Terminal 4 - Images Service
cd apps/images-service
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

# Terminal 5 - Reports Service
cd apps/reports-service
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

# Terminal 6 - Frontend
cd apps/web
yarn start
```

### 6. Accéder aux services

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | - |
| Auth API | http://localhost:8001/docs | - |
| Cases API | http://localhost:8002/docs | - |
| Workflow API | http://localhost:8003/docs | - |
| Images API | http://localhost:8004/docs | - |
| Reports API | http://localhost:8005/docs | - |
| Grafana | http://localhost:3001 | admin / pixtral2025 |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| n8n | http://localhost:5678 | admin / pixtral2025 |

## Déploiement Production

### 1. Préparer les variables d'environnement

Créer un fichier `.env.prod` :

```env
# PostgreSQL
POSTGRES_USER=pixtral_prod_user
POSTGRES_PASSWORD=CHANGE_ME_SECURE_PASSWORD

# Databases URLs
AUTH_DB_URL=postgresql://pixtral_prod_user:PASSWORD@postgres:5432/auth_db
CASES_DB_URL=postgresql://pixtral_prod_user:PASSWORD@postgres:5432/cases_db
WORKFLOW_DB_URL=postgresql://pixtral_prod_user:PASSWORD@postgres:5432/workflow_db
IMAGES_DB_URL=postgresql://pixtral_prod_user:PASSWORD@postgres:5432/images_db
REPORTS_DB_URL=postgresql://pixtral_prod_user:PASSWORD@postgres:5432/reports_db

# JWT
JWT_SECRET_KEY=GENERATE_SECURE_KEY_HERE

# MinIO
MINIO_ROOT_USER=pixtral_admin
MINIO_ROOT_PASSWORD=CHANGE_ME_SECURE_PASSWORD

# AI
EMERGENT_LLM_KEY=sk-emergent-753468924163d5fC03

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=CHANGE_ME_SECURE_PASSWORD
N8N_USER=admin
N8N_PASSWORD=CHANGE_ME_SECURE_PASSWORD
```

### 2. Build et déploiement

```bash
# Charger les variables
export $(cat .env.prod | xargs)

# Build les images
docker-compose -f infra/docker-compose.prod.yml build

# Démarrer en production
docker-compose -f infra/docker-compose.prod.yml up -d

# Vérifier le statut
docker-compose -f infra/docker-compose.prod.yml ps

# Logs
docker-compose -f infra/docker-compose.prod.yml logs -f
```

### 3. Healthchecks

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

## CI/CD GitHub Actions

### Configuration des secrets GitHub

Aller dans `Settings > Secrets and variables > Actions` et ajouter :

```
DEV_AUTH_DB_URL
DEV_CASES_DB_URL
DEV_WORKFLOW_DB_URL
DEV_IMAGES_DB_URL
DEV_REPORTS_DB_URL
JWT_SECRET_KEY
EMERGENT_LLM_KEY
```

### Workflows disponibles

1. **CI** (`.github/workflows/ci.yml`)
   - Déclencheur : Pull requests vers `main` ou `develop`
   - Actions :
     - Lint backend (ruff)
     - Type check (mypy)
     - Tests unitaires (pytest)
     - Lint frontend (ESLint)
     - Tests frontend (Jest)
     - Build images Docker

2. **CD Dev** (`.github/workflows/cd-dev.yml`)
   - Déclencheur : Push sur `develop`
   - Actions :
     - Build images
     - Migrations DB
     - Déploiement
     - Healthchecks
     - Rollback si échec

## Monitoring

### Prometheus
- URL : http://localhost:9090
- Métriques : CPU, RAM, latence HTTP, taux d'erreur

### Grafana
- URL : http://localhost:3001
- Dashboards pré-configurés pour chaque service

## Troubleshooting

### Service ne démarre pas
```bash
# Vérifier les logs
docker-compose -f infra/docker-compose.dev.yml logs <service-name>

# Vérifier la connectivité DB
psql -h localhost -U pixtral_user -d auth_db
```

### Migrations échouées
```bash
# Recréer les migrations
cd apps/auth-service
alembic downgrade base
alembic revision --autogenerate -m "Fresh start"
alembic upgrade head
```

### Réinitialiser complètement
```bash
bash scripts/stop-all-services.sh
docker-compose -f infra/docker-compose.dev.yml down -v
bash scripts/start-all-services.sh
```

## Backup & Restauration

### Backup PostgreSQL
```bash
pg_dump -h localhost -U pixtral_user auth_db > backup_auth_db.sql
```

### Restauration
```bash
psql -h localhost -U pixtral_user auth_db < backup_auth_db.sql
```

### Backup MinIO
```bash
mc mirror myminio/pixtral-wsi-images ./backup-images/
```
