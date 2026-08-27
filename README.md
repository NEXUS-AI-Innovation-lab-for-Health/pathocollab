# PathoCollab - Plateforme de Collaboration en Pathologie

[![CI Status](https://img.shields.io/badge/CI-passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-Academic-blue)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![Node](https://img.shields.io/badge/node-20+-green)]()
[![Docker](https://img.shields.io/badge/docker-required-blue)]()

## 🏥 Vue d'ensemble

PathoCollab est une plateforme web collaborative pour l'analyse de biopsies entre anatomopathologistes et oncologues, avec assistance IA (GPT-4o). 

**Projet académique** - SAE 6 - Équipe Onco NexCode

### ✨ Fonctionnalités principales

- 🔐 **Authentification JWT** avec gestion des rôles
- 📋 **Gestion de cas** patients et biopsies
- 🔄 **Workflow collaboratif** tour-par-tour avec notifications
- 🖼️ **Images WSI** (Whole Slide Imaging) avec annotations
- 🤖 **Assistance IA** (GPT-4o) pour rapports et détection d'anomalies
- 📊 **Monitoring** temps réel (Prometheus + Grafana)
- 🔌 **Workflows no-code** (n8n)
- 📦 **Architecture microservices** (5 services FastAPI)

---

## 🏗️ Architecture

### Monorepo Turborepo

```
apps/
├── auth-service/      # 🔐 Authentification (FastAPI + PostgreSQL)
├── cases-service/     # 📋 Cas patients (FastAPI + PostgreSQL)
├── workflow-service/  # 🔄 Workflow (FastAPI + PostgreSQL + Redis + Kafka)
├── images-service/    # 🖼️ Images WSI (FastAPI + PostgreSQL + MinIO)
├── reports-service/   # 📝 Rapports IA (FastAPI + PostgreSQL + Qdrant + GPT-4o)
└── web/              # ⚛️ Interface React

packages/
└── shared-types/     # Types partagés

infra/
├── docker-compose.dev.yml   # Environnement de développement
├── docker-compose.prod.yml  # Environnement de production
└── monitoring/              # Prometheus + Grafana
```

### 🔧 Services Backend (FastAPI)

| Service | Port | Base de données | Rôle |
|---------|------|-----------------|------|
| **Auth** | 8001 | PostgreSQL `auth_db` | 🔐 Authentification, JWT, rôles |
| **Cases** | 8002 | PostgreSQL `cases_db` | 📋 Patients, cas BIO-2025-XXXXX |
| **Workflow** | 8003 | PostgreSQL `workflow_db` + Redis | 🔄 Workflow collaboratif, notifications |
| **Images** | 8004 | PostgreSQL `images_db` + MinIO | 🖼️ Upload WSI, annotations |
| **Reports** | 8005 | PostgreSQL `reports_db` + Qdrant | 📝 Rapports IA (GPT-4o + RAG) |

### 🛠️ Infrastructure

| Composant | Port | Utilisation |
|-----------|------|-------------|
| **PostgreSQL** | 5432 | 5 bases de données séparées |
| **Redis** | 6379 | Cache, sessions, workflow memory |
| **MinIO** | 9000/9001 | Stockage images WSI chiffrées |
| **Redpanda** | 9092 | Bus d'événements (Kafka-compatible) |
| **Qdrant** | 6333 | Vector DB pour RAG |
| **n8n** | 5678 | Workflows no-code |
| **Prometheus** | 9090 | Métriques |
| **Grafana** | 3001 | Dashboards |

---

## 🚀 Démarrage rapide

### Prérequis

| Logiciel | Version | Installation |
|----------|---------|--------------|
| **Docker** | ≥ 24.0 | [Get Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | ≥ 2.20 | Inclus avec Docker Desktop |
| **Node.js** | ≥ 20.0 | [nodejs.org](https://nodejs.org/) |
| **Python** | ≥ 3.11 | [python.org](https://www.python.org/) |
| **Yarn** | ≥ 1.22 | `npm install -g yarn` |

### Installation 

```bash
# Cloner le repository
git clone https://github.com/NEXUS-AI-Innovation-lab-for-Health/pathocollab.git
cd pathocollab

# Build les images du docker
docker compose -f infra/docker-compose.dev.yml up -d --build

# Installer les dépendances frontend
cd frontend
npm install --legacy-peer-deps

# Lancer le Frontend
npm start
```

### 🌐 Accéder à l'application

| Service | URL | Credentials |
|---------|-----|-------------|
| **🖥️ Frontend** | http://localhost:3000 | Créer un compte |
| 🔐 Auth API Docs | http://localhost:8001/docs | - |
| 📋 Cases API Docs | http://localhost:8002/docs | - |
| 🔄 Workflow API Docs | http://localhost:8003/docs | - |
| 🖼️ Images API Docs | http://localhost:8004/docs | - |
| 📝 Reports API Docs | http://localhost:8005/docs | - |
| 📊 **Grafana** | http://localhost:3001 | admin / pixtral2025 |
| 📦 **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| 🔌 **n8n** | http://localhost:5678 | admin / pixtral2025 |

### 🧪 Tester l'installation

```bash
# Healthchecks
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # Cases Service
curl http://localhost:8003/health  # Workflow Service
curl http://localhost:8004/health  # Images Service
curl http://localhost:8005/health  # Reports Service
```

### 🧪 Utilisateurs Authentification
```bash
[ADMIN]
ID (email) : admin@gmail.com
PASSWORD : admin1234

[ANATOMOPATHOLOGISTE]
ID (email) : smith@gmail.com
PASSWORD : smith1234

[RADIOLOGUE]
ID (email) : jack@gmail.com
PASSWORD : jack1234

[ONCOLOGUE]
ID (email) : louna@gmail.com
PASSWORD : louna1234

[GENERALISTE]
ID (email) : alice@gmail.com
PASSWORD : alice1234
```

### Ajout d'image dans la base de données :
```bash 
[Site officiel de récupération de pathologie]
https://portal.gdc.cancer.gov/analysis_page?app=Downloads
[API Upload image wsi à un patient (Quelques minutes)]
http://localhost:8004/docs#/WSI/upload_and_convert_wsi_api_wsi_upload_and_convert_post
```

---

## Développement

### Structure d'un service FastAPI

```
auth-service/
├── alembic/           # Migrations DB
├── app/
│   ├── models/       # Modèles Pydantic & SQLAlchemy
│   ├── routes/       # Endpoints API
│   ├── services/     # Logique métier
│   ├── utils/        # Utilitaires
│   └── main.py       # Point d'entrée
├── tests/
├── .env
├── alembic.ini
└── requirements.txt
```

### Workflow collaboratif

1. Admin crée un cas → sélectionne les spécialistes
2. Notifications envoyées aux spécialistes (ordre défini)
3. Chaque spécialiste analyse à son tour :
   - Visualise les images WSI (OpenSeadragon)
   - Ajoute des annotations (manuelles + suggestions IA)
   - Rédige son rapport (assisté par LLM)
4. Chat collaboratif entre spécialistes
5. Rapport final synthétisé par IA
6. Validation et signature numérique

## CI/CD

### GitHub Actions

- **CI** (`.github/workflows/ci.yml`):
  - Lint & tests unitaires
  - Build des images Docker
  - Coverage ≥ 80% pour backend

- **CD Dev** (`.github/workflows/cd-dev.yml`):
  - Déploiement automatique sur push `develop`
  - Migrations DB
  - Healthchecks


## Sécurité & RGPD

- Chiffrement des images au repos (MinIO)
- Tokens JWT avec expiration
- Audit log complet (toutes les actions tracées)
- Conformité FHIR pour interopérabilité
- Backup régulier des bases de données

## Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md)

## Licence

PathoCollab - Onco Nexcode 
