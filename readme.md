# 🎭 PW-Analyst

**Analyseur de résultats de tests Playwright** - Une application Django pour visualiser, analyser et gérer les résultats de vos tests Playwright avec intégration CI/CD.

## 📋 Table des matières

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Intégration CI/CD](#intégration-cicd)
- [API](#api)
- [Déploiement](#déploiement)
- [Développement](#développement)
- [Contribution](#contribution)

## 🎯 Aperçu

PW-Analyst est une application web Django conçue pour centraliser et analyser les résultats de tests Playwright. Elle permet aux équipes de développement de suivre l'évolution de leurs tests, identifier les régressions et analyser les tendances de qualité.

### ✨ Fonctionnalités principales

- **📊 Dashboard interactif** - Vue d'ensemble des résultats de tests
- **📈 Analyse de tendances** - Évolution de la qualité dans le temps
- **🔍 Recherche avancée** - Filtrage par tags, statuts, fichiers
- **🏷️ Système de tags** - Catégorisation flexible des tests
- **🔗 Intégration CI/CD** - Récupération automatique depuis GitLab/GitHub
- **📝 Commentaires** - Annotation des tests pour documentation
- **📱 Interface responsive** - Compatible mobile et desktop
- **⚡ Performance optimisée** - Pagination et lazy loading

## 🛠️ Stack technique

### Backend

- **Django 5.2.5** - Framework web Python
- **SQLite** - Base de données (configurable pour PostgreSQL/MySQL)
- **Django Cotton** - Composants de templates réutilisables
- **Django Compressor** - Optimisation des assets statiques

### Frontend

- **Tailwind CSS** - Framework CSS utilitaire
- **JavaScript Vanilla** - Interactions côté client
- **HTMX** (optionnel) - Interactions AJAX simplifiées

### Intégrations

- **GitLab API** - Récupération d'artifacts CI/CD
- **GitHub Actions API** - Récupération d'artifacts GitHub
- **Requests** - Client HTTP pour les APIs externes

### Outils de développement

- **WhiteNoise** - Gestion des fichiers statiques
- **Django LibSass** - Compilation SCSS
- **Compressor** - Minification CSS/JS

## 🚀 Installation

### Prérequis

- Python 3.8+
- pip
- Git

### Installation locale

1. **Cloner le repository**

```bash
git clone https://github.com/votre-username/pw-analyst.git
cd pw-analyst
```

2. **Créer un environnement virtuel**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows
```

3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

4. **Configurer la base de données**

```bash
python manage.py migrate
```

5. **Créer un superutilisateur**

```bash
python manage.py createsuperuser
```

6. **Collecter les fichiers statiques**

```bash
python manage.py collectstatic
```

7. **Lancer le serveur de développement**

```bash
python manage.py runserver
```

L'application sera accessible sur `http://localhost:8000`

## ⚙️ Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine du projet :

```env
# Sécurité
SECRET_KEY=votre-clé-secrète-très-longue-et-complexe
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Base de données (optionnel, SQLite par défaut)
DATABASE_URL=postgres://user:password@localhost:5432/pw_analyst

# CI/CD (optionnel)
GITLAB_DEFAULT_URL=https://gitlab.com
GITHUB_DEFAULT_URL=https://api.github.com
```

### Configuration de base de données

#### SQLite (par défaut)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

#### PostgreSQL

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'pw_analyst',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 📖 Utilisation

### 1. Créer un projet

1. Accédez à l'admin Django : `http://localhost:8000/admin/`
2. Créez un nouveau **Projet**
3. Optionnellement, configurez une **Configuration CI**

### 2. Importer des résultats de tests

#### Upload manuel

1. Allez sur "Importer des résultats"
2. Sélectionnez votre projet
3. Uploadez votre fichier JSON Playwright

#### Récupération automatique CI/CD

1. Configurez une intégration CI/CD dans l'admin
2. Associez-la à votre projet
3. Utilisez l'option "Récupérer depuis CI"

### 3. Analyser les résultats

- **Vue d'ensemble** : Dashboard avec métriques globales
- **Tests** : Liste détaillée avec filtres et recherche
- **Exécutions** : Historique des runs de tests
- **Tags** : Gestion et filtrage par catégories

### 4. Gestion des tags

```python
# Exemple d'utilisation des tags
# Les tags sont automatiquement extraits du JSON Playwright
# ou peuvent être ajoutés manuellement

# Dans vos tests Playwright :
test.describe('Login @auth @critical', () => {
  test('should login successfully', async ({ page }) => {
    // votre test
  });
});
```

## 🔗 Intégration CI/CD

### GitLab CI/CD

1. **Configuration GitLab**

```yaml
# .gitlab-ci.yml
test:
  stage: test
  script:
    - npm ci
    - npx playwright test --reporter=json --outputFile=test-results.json
  artifacts:
    when: always
    paths:
      - test-results.json
    expire_in: 1 week
```

2. **Configuration dans PW-Analyst**

- URL GitLab : `https://gitlab.com`
- ID du projet : `12345` (visible dans Settings → General)
- Token d'accès : Token avec scope `read_api`
- Nom du job : `test`
- Chemin JSON : `test-results.json`

### GitHub Actions

1. **Configuration GitHub Actions**

```yaml
# .github/workflows/playwright.yml
name: Playwright Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npx playwright test --reporter=json --outputFile=test-results.json
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-results
          path: test-results.json
```

2. **Configuration dans PW-Analyst**

- Repository : `owner/repo`
- Token d'accès : GitHub Personal Access Token
- Workflow : `Playwright Tests`
- Artifact : `playwright-results`
- Fichier JSON : `test-results.json`

## 🔌 API

### Endpoints principaux

```http
# Projets
GET    /api/projects/                 # Liste des projets
POST   /api/projects/                 # Créer un projet
GET    /api/projects/{id}/            # Détail d'un projet

# Exécutions
GET    /api/executions/               # Liste des exécutions
POST   /api/executions/               # Importer une exécution
GET    /api/executions/{id}/          # Détail d'une exécution

# Tests
GET    /api/tests/                    # Liste des tests
GET    /api/tests/{id}/               # Détail d'un test
PUT    /api/tests/{id}/comment/       # Ajouter un commentaire

# CI/CD
POST   /api/ci/fetch/                 # Récupérer depuis CI
GET    /api/ci/status/                # Status de la connexion CI
```

### Exemple d'utilisation

```python
import requests

# Importer des résultats
with open('test-results.json', 'r') as f:
    data = {
        'project_id': 1,
        'json_data': f.read()
    }
    response = requests.post('http://localhost:8000/api/executions/', 
                           json=data)
```

## 🚀 Déploiement

### Déploiement avec Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./db.sqlite3:/app/db.sqlite3
```

### Déploiement sur Heroku

```bash
# Prérequis : Heroku CLI installé
heroku create pw-analyst
heroku config:set SECRET_KEY="votre-clé-secrète"
heroku config:set DEBUG=False
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### Variables d'environnement de production

```env
DEBUG=False
SECRET_KEY=votre-clé-secrète-de-production-très-longue
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
DATABASE_URL=postgres://...
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
```

## 🔧 Développement

### Structure du projet

```
pw-analyst/
├── core/                     # Application principale
│   ├── models.py            # Modèles de données
│   ├── views.py             # Vues et logique métier
│   ├── admin.py             # Interface d'administration
│   ├── urls.py              # Routes URL
│   ├── services/            # Services externes (CI/CD)
│   ├── management/commands/ # Commandes de gestion
│   └── templatetags/        # Filtres de template
├── templates/               # Templates Django
│   ├── base.html           # Template de base
│   ├── cotton/             # Composants Cotton
│   └── ...
├── static/                  # Fichiers statiques source
├── staticfiles/            # Fichiers statiques collectés
├── myproject/              # Configuration Django
├── requirements.txt        # Dépendances Python
└── manage.py              # Script de gestion Django
```

### Commandes utiles

```bash
# Développement
python manage.py runserver          # Serveur de développement
python manage.py shell              # Shell Django
python manage.py dbshell            # Shell base de données

# Migrations
python manage.py makemigrations     # Créer des migrations
python manage.py migrate            # Appliquer les migrations
python manage.py showmigrations     # Voir le statut des migrations

# Tests
python manage.py test               # Lancer les tests
python manage.py test core          # Tests d'une app spécifique

# Gestion des données
python manage.py loaddata fixtures/sample_data.json
python manage.py dumpdata core > backup.json

# Import personnalisé
python manage.py import_playwright data/test-results.json --project=1
```

### Ajout de nouvelles fonctionnalités

1. **Nouveau modèle**

```python
# core/models.py
class NouveuModele(models.Model):
    name = models.CharField(max_length=200)
    
    class Meta:
        verbose_name = "Nouveau Modèle"
```

2. **Migration**

```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Admin**

```python
# core/admin.py
@admin.register(NouveuModele)
class NouveauModeleAdmin(admin.ModelAdmin):
    list_display = ['name']
```

## 🤝 Contribution

### Guidelines

1. **Fork** le repository
2. Créez une **branche feature** : `git checkout -b feature/ma-fonctionnalite`
3. **Commitez** vos changements : `git commit -m 'Ajout de ma fonctionnalité'`
4. **Push** vers la branche : `git push origin feature/ma-fonctionnalite`
5. Ouvrez une **Pull Request**

### Standards de code

- **PEP 8** pour le Python
- **Black** pour le formatage automatique
- **isort** pour l'organisation des imports
- **Docstrings** pour la documentation

```bash
# Installation des outils de développement
pip install black isort flake8

# Formatage du code
black .
isort .
flake8 .
```

### Tests

```python
# core/tests.py
from django.test import TestCase
from .models import Project

class ProjectTestCase(TestCase):
    def test_project_creation(self):
        project = Project.objects.create(
            name="Test Project",
            description="Test description"
        )
        self.assertEqual(project.name, "Test Project")
```

## 📄 Licence

Ce projet est sous licence Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0).

**Vous êtes libre de :**
- 🔄 Partager, copier et redistribuer le matériel
- 🔧 Adapter, modifier et construire à partir du matériel

**Sous les conditions suivantes :**
- 📝 **Attribution** : Vous devez créditer l'auteur original (Damien Hoffmann)
- 💰 **Non Commercial** : Vous ne pouvez pas utiliser ce matériel à des fins commerciales
- 🔄 **Partage dans les mêmes conditions** : Si vous modifiez le projet, vous devez le distribuer sous la même licence

Voir le fichier `LICENSE` pour plus de détails ou visitez [Creative Commons](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## 🆘 Support

- **Issues** : [GitHub Issues](https://github.com/votre-username/pw-analyst/issues)
- **Documentation** : [Wiki du projet](https://github.com/votre-username/pw-analyst/wiki)
- **Email** : <support@votre-domaine.com>

## 🙏 Remerciements

- [Django](https://djangoproject.com/) - Framework web Python
- [Playwright](https://playwright.dev/) - Framework de test
- [Tailwind CSS](https://tailwindcss.com/) - Framework CSS
- [Django Cotton](https://django-cotton.com/) - Composants Django

---

**Développé avec ❤️ par [Damien HOFFMANN](https://github.com/votre-username)**
