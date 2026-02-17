# Guide de Contribution - Pixtral Platform

Merci de votre intérêt pour contribuer au projet Pixtral ! Ce guide vous aidera à démarrer.

## Table des matières

1. [Code de conduite](#code-de-conduite)
2. [Comment contribuer](#comment-contribuer)
3. [Structure du projet](#structure-du-projet)
4. [Conventions de code](#conventions-de-code)
5. [Tests](#tests)
6. [Pull Requests](#pull-requests)
7. [Issues](#issues)

---

## Code de conduite

En participant à ce projet, vous acceptez de respecter un environnement inclusif et respectueux. Soyez professionnel et courtois.

---

## Comment contribuer

### Workflow Git

1. **Fork** le repository
2. **Créer une branche** depuis `develop`
   ```bash
   git checkout -b feature/ma-fonctionnalite
   # ou
   git checkout -b fix/mon-bug
   ```
3. **Commiter** vos changements
4. **Pousser** vers votre fork
5. **Créer une Pull Request** vers `develop`

### Branches

- `main` : Production (protégée)
- `develop` : Développement (branche par défaut)
- `feature/*` : Nouvelles fonctionnalités
- `fix/*` : Corrections de bugs
- `hotfix/*` : Corrections urgentes en production

### Commits

Utiliser le format Conventional Commits :

```
type(scope): description courte

Description détaillée (optionnel)

Fixes #123
```

**Types** :
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage (pas de changement de code)
- `refactor`: Refactoring
- `test`: Ajout de tests
- `chore`: Tâches de maintenance

**Exemples** :
```bash
feat(auth): ajouter authentification OAuth2
fix(workflow): corriger la notification des spécialistes
docs(readme): mettre à jour les instructions d'installation
```

---

## Structure du projet

### Monorepo

```
/
├── apps/
│   ├── auth-service/       # Service d'authentification
│   ├── cases-service/      # Service des cas
│   ├── workflow-service/   # Service de workflow
│   ├── images-service/     # Service d'images
│   ├── reports-service/    # Service de rapports
│   └── web/               # Frontend React
├── packages/
│   └── shared-types/      # Types partagés
├── infra/
│   ├── docker-compose.*.yml
│   ├── monitoring/
│   └── postgres/
├── scripts/
├── .github/workflows/
└── tests/
```

### Ajouter un nouveau service

1. Créer le dossier dans `apps/`
2. Suivre la structure standard :
   ```
   new-service/
   ├── app/
   │   ├── models/
   │   ├── routes/
   │   ├── services/
   │   ├── utils/
   │   └── main.py
   ├── alembic/
   ├── tests/
   ├── requirements.txt
   ├── .env
   └── Dockerfile
   ```
3. Ajouter la base de données dans `infra/postgres/init-multiple-databases.sh`
4. Ajouter le service dans `docker-compose.*.yml`
5. Ajouter les migrations Alembic
6. Mettre à jour les workflows CI/CD

---

## Conventions de code

### Backend (Python/FastAPI)

#### Style
- **Formatter** : Black (line-length=100)
- **Linter** : Ruff
- **Type checker** : mypy

```bash
# Formater le code
black app/ --line-length=100

# Linter
ruff check app/

# Type checking
mypy app/ --ignore-missing-imports
```

#### Conventions

**Naming** :
- Variables, fonctions : `snake_case`
- Classes : `PascalCase`
- Constantes : `UPPER_SNAKE_CASE`
- Fichiers : `snake_case.py`

**Imports** :
```python
# Standard library
import os
from datetime import datetime

# Third-party
from fastapi import FastAPI, Depends
from pydantic import BaseModel

# Local
from app.models import User
from app.services import AuthService
```

**Docstrings** :
```python
def create_user(user_data: UserCreate) -> User:
    """Créer un nouvel utilisateur.
    
    Args:
        user_data: Données de l'utilisateur à créer
        
    Returns:
        L'utilisateur créé
        
    Raises:
        HTTPException: Si l'email existe déjà
    """
    pass
```

**Models Pydantic** :
```python
class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    
    class Config:
        from_attributes = True  # Pour SQLAlchemy
```

**Endpoints FastAPI** :
```python
@router.post("/users", response_model=User, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> User:
    """Créer un utilisateur"""
    return await UserService.create(db, user_data)
```

#### Base de données

**Migrations Alembic** :
```bash
# Créer une migration
alembic revision --autogenerate -m "Description du changement"

# Appliquer les migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

**Models SQLAlchemy** :
```python
class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

### Frontend (React/JavaScript)

#### Style
- **Formatter** : Prettier
- **Linter** : ESLint

```bash
# Formater
yarn prettier --write "src/**/*.{js,jsx,json,css}"

# Linter
yarn lint
```

#### Conventions

**Naming** :
- Composants : `PascalCase.js`
- Hooks : `useCamelCase.js`
- Utilitaires : `camelCase.js`
- Constantes : `UPPER_SNAKE_CASE`

**Composants** :
```jsx
// Composant fonctionnel avec props typées
const CaseCard = ({ caseData, onClick }) => {
  return (
    <div onClick={onClick} data-testid="case-card">
      <h3>{caseData.title}</h3>
    </div>
  );
};

export default CaseCard;
```

**Hooks personnalisés** :
```jsx
const useAuth = () => {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    // Logic
  }, []);
  
  return { user, login, logout };
};
```

**API Calls** :
```jsx
// Utiliser axios avec try/catch
const fetchCases = async () => {
  try {
    const response = await axios.get(`${API_URL}/api/cases`);
    return response.data;
  } catch (error) {
    console.error('Error fetching cases:', error);
    toast.error('Erreur lors du chargement');
    throw error;
  }
};
```

**Data-testid** :
TOUJOURS ajouter `data-testid` aux éléments interactifs :
```jsx
<Button data-testid="submit-button" onClick={handleSubmit}>
  Soumettre
</Button>
```

---

## Tests

### Backend Tests (pytest)

**Structure** :
```
service/
├── app/
└── tests/
    ├── conftest.py           # Fixtures
    ├── test_routes.py        # Tests endpoints
    ├── test_services.py      # Tests logique métier
    └── test_models.py        # Tests modèles
```

**Exemple** :
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User",
            "role": "anatomopathologiste"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"

@pytest.fixture
def test_user(db):
    # Setup
    user = create_test_user()
    yield user
    # Teardown
    db.delete(user)
    db.commit()
```

**Lancer les tests** :
```bash
# Tous les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=term --cov-report=html

# Tests spécifiques
pytest tests/test_routes.py::test_create_user
```

### Frontend Tests (Jest + React Testing Library)

**Exemple** :
```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Login from './Login';

test('login form submission', async () => {
  render(<Login />);
  
  const emailInput = screen.getByTestId('email-input');
  const passwordInput = screen.getByTestId('password-input');
  const submitButton = screen.getByTestId('login-submit-button');
  
  fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
  fireEvent.change(passwordInput, { target: { value: 'password123' } });
  fireEvent.click(submitButton);
  
  await waitFor(() => {
    expect(screen.getByText('Connexion réussie')).toBeInTheDocument();
  });
});
```

**Lancer les tests** :
```bash
yarn test
yarn test --coverage
```

---

## Pull Requests

### Checklist avant de soumettre

- [ ] Code formaté (Black/Prettier)
- [ ] Lint passé (Ruff/ESLint)
- [ ] Tests écrits et passants
- [ ] Coverage ≥ 80% (backend)
- [ ] Migrations Alembic créées si nécessaire
- [ ] Documentation mise à jour
- [ ] `data-testid` ajoutés (frontend)
- [ ] Pas de secrets/credentials dans le code

### Template PR

```markdown
## Description
Brève description des changements

## Type de changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Tests
- [ ] Tests unitaires ajoutés
- [ ] Tests d'intégration ajoutés
- [ ] Tests manuels effectués

## Screenshots (si applicable)

## Checklist
- [ ] Code linted
- [ ] Tests passants
- [ ] Documentation mise à jour

## Issues liées
Fixes #123
Related to #456
```

### Review process

1. Créer la PR vers `develop`
2. CI/CD automatique (lint + tests + build)
3. Review par au moins 1 membre de l'équipe
4. Corrections si nécessaire
5. Merge squash (1 commit final)

---

## Issues

### Créer une issue

Utiliser les templates :

**Bug Report** :
```markdown
**Description**
Description claire du bug

**Reproduction**
1. Aller à '...'
2. Cliquer sur '...'
3. Erreur apparaît

**Comportement attendu**
Ce qui devrait se passer

**Screenshots**

**Environnement**
- OS: [e.g. Ubuntu 22.04]
- Browser: [e.g. Chrome 120]
- Version: [e.g. 1.0.0]
```

**Feature Request** :
```markdown
**Problème**
Quel problème cela résout-il ?

**Solution proposée**
Description de la fonctionnalité

**Alternatives**
Autres solutions envisagées

**Contexte**
Informations supplémentaires
```

### Labels

- `bug` : Bug à corriger
- `enhancement` : Nouvelle fonctionnalité
- `documentation` : Amélioration docs
- `good first issue` : Bon pour débutants
- `help wanted` : Aide recherchée
- `priority: high` : Priorité haute
- `wontfix` : Ne sera pas corrigé

---

## Questions

Pour toute question :
- Ouvrir une Discussion GitHub
- Contacter l'équipe via [email]

Merci de contribuer à Pixtral ! 🎉
