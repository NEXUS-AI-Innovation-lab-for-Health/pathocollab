# Architecture Pixtral - Plateforme de Collaboration en Pathologie

## Vue d'ensemble

Pixtral est une plateforme de collaboration médicale conçue pour l'analyse collaborative de biopsies entre anatomopathologistes et oncologues, avec assistance IA.

## Schéma d'architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│                  Port 3000 - apps/web                   │
└──────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST
                              │
        ┌─────────────────┴─────────────────┐
        │                                  │
        │      BACKEND MICROSERVICES      │
        │         (FastAPI x5)             │
        │                                  │
        ├──────────┬─────────┬─────────┤
        │          │         │         │
   ┌────┴─────  ┌─┴───────  ┌┴──────────┐
   │         │  │         │  │           │
┌──┴─────  ┌┴─┴────  ┌┴─┴────  ┌┴───────  ┌┴─────────┐
│ Auth  │ │Cases│ │Work-│ │Images│ │Reports   │
│Service│ │Svc  │ │flow │ │ Svc  │ │ Service  │
│:8001  │ │:8002│ │:8003 │ │:8004 │ │ :8005    │
└──┬─────┘ └─┬────┘ └─┬────┘ └─┬─────┘ └─┬─────────┘
   │         │       │       │          │
   │         │       │       │          │
┌──┴────────┴───────┴───────┴──────────┴──────────┐
│                                                  │
│          COUCHE INFRASTRUCTURE                  │
│                                                  │
├──────────────────────────────────────────────────┤
│ PostgreSQL (5 DB) | Redis | MinIO | Redpanda  │
│ Qdrant | n8n | Prometheus | Grafana           │
└──────────────────────────────────────────────────┘
```

## Services Backend

### 1. Auth Service (Port 8001)
**Rôle** : Authentification et gestion des utilisateurs

**Base de données** : PostgreSQL `auth_db`

**Fonctionnalités** :
- Authentification email/mot de passe
- Génération de tokens JWT (access + refresh)
- Gestion des rôles : `admin`, `anatomopathologiste`, `oncologue`
- Validation et renouvellement de tokens
- Historique de connexion

**Endpoints principaux** :
- `POST /api/auth/register` : Création de compte
- `POST /api/auth/login` : Connexion
- `GET /api/auth/me` : Profil utilisateur
- `GET /api/auth/users/{user_id}` : Récupérer un utilisateur

**Technologies** :
- FastAPI
- SQLAlchemy
- Passlib (bcrypt)
- PyJWT
- Redis (sessions)

---

### 2. Cases Service (Port 8002)
**Rôle** : Gestion des cas patients et dossiers cliniques

**Base de données** : PostgreSQL `cases_db` (Supabase-compatible)

**Fonctionnalités** :
- Création de dossiers patients (PAT-XXXXX)
- Création de cas de biopsie (BIO-2025-XXXXXX)
- Gestion des informations cliniques
- Association spécialistes ↔ cas
- Suivi du statut des cas (pending, in_progress, completed)

**Endpoints principaux** :
- `POST /api/patients` : Créer un patient
- `GET /api/patients/{id}` : Détail patient
- `POST /api/cases` : Créer un cas
- `GET /api/cases` : Lister les cas
- `PATCH /api/cases/{id}/status` : Changer le statut

**Modèles de données** :
```python
Patient:
  - id: PAT-XXXXX
  - full_name
  - age, gender
  - medical_history
  - symptoms
  - imaging_notes

Case:
  - id: BIO-2025-XXXXXX
  - patient_id
  - title, description
  - status (enum)
  - created_by
  - assigned_specialists (JSON)
```

---

### 3. Workflow Service (Port 8003)
**Rôle** : Orchestration du workflow collaboratif tour-par-tour

**Bases de données** : 
- PostgreSQL `workflow_db`
- Redis (mémoire process)
- Redpanda/Kafka (bus d'événements)

**Fonctionnalités** :
- Workflow tour-par-tour automatique
- Notification des spécialistes (Kafka + in-app)
- Gestion des transitions d'étapes
- Historique complet des actions
- Support mode offline (synchronisation ultérieure)

**Endpoints principaux** :
- `POST /api/workflows` : Créer un workflow
- `GET /api/workflows/case/{case_id}` : Workflow d'un cas
- `POST /api/workflows/{id}/advance` : Passer à l'étape suivante
- `GET /api/notifications/user/{user_id}` : Notifications utilisateur
- `PATCH /api/notifications/{id}/read` : Marquer comme lu

**Pattern de workflow** :
```
Spécialiste A (en cours) → Notifié
   ↓ Analyse terminée
Spécialiste B (en attente) → Notifié
   ↓ Analyse terminée
Spécialiste C (en attente) → Notifié
   ↓ Analyse terminée
Cas complété → Notification à tous
```

---

### 4. Images Service (Port 8004)
**Rôle** : Gestion des images WSI et annotations

**Bases de données** :
- PostgreSQL `images_db` (métadonnées)
- MinIO (stockage binaire)

**Fonctionnalités** :
- Upload d'images de lames (WSI) vers MinIO
- Chiffrement au repos
- Génération d'URLs présignées
- Annotations manuelles et assistées par IA
- Filtrage et recherche d'annotations

**Endpoints principaux** :
- `POST /api/images/upload` : Upload image WSI
- `GET /api/images/case/{case_id}` : Images d'un cas
- `GET /api/images/{id}/url` : URL présignée
- `POST /api/annotations` : Créer une annotation
- `GET /api/annotations/image/{image_id}` : Annotations d'une image

**Modèle Annotation** :
```python
Annotation:
  - type: manual | ai_detected | ai_assisted
  - coordinates: {x, y, width, height}
  - label: str
  - confidence: float (pour IA)
  - notes: str
```

**MinIO Buckets** :
- `pixtral-wsi-images` : Images principales
- `pixtral-images` : Images annexes

---

### 5. Reports Service (Port 8005)
**Rôle** : Génération de rapports avec IA (GPT-4o) et RAG

**Bases de données** :
- PostgreSQL `reports_db`
- Qdrant (vector DB pour RAG)

**Fonctionnalités** :
- Rédaction de rapports individuels
- Assistance IA pour génération de texte
- RAG (Retrieval-Augmented Generation) avec historique
- Synthèse automatique de rapports multiples
- Marquage de rapports finaux

**Endpoints principaux** :
- `POST /api/reports` : Créer un rapport
- `POST /api/reports/assist` : Générer avec IA
- `GET /api/reports/case/{case_id}` : Tous les rapports d'un cas
- `PATCH /api/reports/{id}/finalize` : Marquer comme final

**Intelligence Artificielle** :
- **Modèle texte** : GPT-4o (via `emergentintegrations`)
- **Modèle vision** : GPT-4o Vision (analyse d'images)
- **RAG** : Qdrant (embeddings + recherche sémantique)

**Workflow IA** :
```python
1. Utilisateur demande assistance
2. Service récupère :
   - Contexte patient
   - Annotations images
   - Rapports précédents
   - Documents similaires (RAG/Qdrant)
3. Prompt construit et envoyé à GPT-4o
4. Réponse formatée et retournée
5. Rapport stocké + embedding dans Qdrant
```

---

## Infrastructure

### PostgreSQL (5 bases de données)
Une instance PostgreSQL 16 héberge 5 bases séparées :
- `auth_db` : Utilisateurs, tokens
- `cases_db` : Patients, cas
- `workflow_db` : Workflows, notifications
- `images_db` : Métadonnées images, annotations
- `reports_db` : Rapports

**Migrations** : Alembic (indépendantes par service)

### Redis
Utilisé pour :
- Sessions utilisateurs (auth)
- Cache (workflow)
- Mémoire temporaire des événements offline

### MinIO
Stockage objet S3-compatible :
- Images WSI chiffrées
- Fichiers volumineux
- Backups

### Redpanda (Kafka)
Bus d'événements :
- Notifications asynchrones
- Événements de workflow
- Audit log

### Qdrant
Base de données vectorielle :
- Embeddings de rapports
- Recherche sémantique (RAG)
- Similarité de cas

### n8n
Automation no-code :
- Workflows personnalisés
- Intégrations externes
- Webhooks

### Prometheus + Grafana
Monitoring :
- Métriques temps réel
- Dashboards par service
- Alertes

---

## Frontend (React)

### Pages principales
1. **Login** (`/`) : Authentification
2. **Dashboard** (`/dashboard`) : Vue d'ensemble des cas
3. **Case Detail** (`/cases/:id`) : Détail d'un cas
4. **Image Viewer** (`/cases/:id/images`) : Visualisation WSI
5. **Report Editor** (`/cases/:id/report`) : Éditeur de rapport

### Composants clés
- **ImageViewer** : OpenSeadragon pour zoom d'images WSI
- **AnnotationTool** : Outils de dessin et labeling
- **ChatPanel** : Discussion entre spécialistes
- **NotificationCenter** : Centre de notifications
- **AIAssistant** : Panneau d'assistance IA

### Technologies
- React 19
- React Router v7
- Shadcn UI (composants)
- Tailwind CSS
- Axios (API calls)
- Sonner (toasts)

---

## Sécurité

### Authentification
- JWT avec access token (30 min) + refresh token (7 jours)
- Tokens stockés en localStorage (dev) / httpOnly cookies (prod)
- Middleware de vérification sur chaque route protégée

### Autorisation
Rôles :
- **admin** : Toutes permissions
- **anatomopathologiste** : Analyse de lames, annotations
- **oncologue** : Consultation, rapports

### Données sensibles
- Chiffrement images au repos (MinIO)
- Connexions PostgreSQL chiffrées (SSL)
- Pas de logs de données patients
- Audit log complet (qui a fait quoi et quand)

### RGPD & HIPAA
- Anonymisation possible des données
- Droit à l'oubli
- Export de données
- Consentement explicit

---

## CI/CD

### Pipeline CI
1. **Lint** : Ruff (Python), ESLint (JS)
2. **Type check** : mypy
3. **Tests** : pytest (backend), Jest (frontend)
4. **Coverage** : ≥ 80% pour backend
5. **Build** : Docker images
6. **Push** : GitHub Container Registry

### Pipeline CD
1. **Migrations** : Alembic upgrade head
2. **Déploiement** : Docker Compose
3. **Healthchecks** : Tous les services
4. **Rollback** : Si healthcheck échoue
5. **Notifications** : Équipe alertée

---

## Scalabilité

### Horizontale
- Chaque service peut être répliqué (stateless)
- Load balancer devant les services
- PostgreSQL avec read replicas
- Redis Cluster

### Verticale
- Augmentation CPU/RAM par conteneur
- Optimisation des requêtes DB
- Cache aggressif (Redis)

### Future optimizations
- Kubernetes pour orchestration
- CDN pour images statiques
- Compression d'images WSI
- Pagination systématique

---

## Maintenance

### Backups
- **PostgreSQL** : pg_dump quotidien
- **MinIO** : Replication vers S3
- **Qdrant** : Snapshots

### Updates
- Rolling updates sans downtime
- Tests en staging avant prod
- Feature flags pour nouvelles fonctionnalités

### Logging
- Logs structurés (JSON)
- Rotation automatique
- Centralisation (futurs : ELK, Loki)
