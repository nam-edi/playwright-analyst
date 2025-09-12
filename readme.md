# 🎭 PW-Analyst

**Analyseur de résultats de tests Playwright** - Une application Django pour visualiser, analyser et gérer les résultats de vos tests Playwright avec intégration CI/CD.

![Django Version](https://img.shields.io/badge/Django-5.2.5-green.svg)
![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)
![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)

## 📋 Table des matières

- [Aperçu](#-aperçu)
- [Installation](#-installation)
- [Configuration](#️-configuration)
- [Déploiement](#-déploiement)
- [Développement](#-développement)
- [Troubleshooting](#-troubleshooting)
- [Contribution](#-contribution)
- [Licence](#-licence)

## 🎯 Aperçu

PW-Analyst est une application web Django conçue pour centraliser et analyser les résultats de tests Playwright. Elle permet aux équipes de développement de suivre l'évolution de leurs tests, identifier les régressions et analyser les tendances de qualité.

**Documentation complète disponible directement dans l'interface de l'application.**

## 🚀 Installation

### Prérequis

- Python 3.8+
- pip
- Git

### Installation locale

1. **Cloner le repository**

```bash
git clone https://github.com/nam-edi/playwright-analyst.git
cd playwright-analyst
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
CMD ["gunicorn", "pw_analyst.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: "3.8"
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

# Collecte des fichiers statiques
python manage.py collectstatic      # Collecter les fichiers statiques
python manage.py collectstatic --clear --noinput  # Forcer la recollecte
```

## 🔧 Troubleshooting

### Problèmes courants

#### Erreur de migration

```bash
# Solution : Réinitialiser la base de données
python manage.py migrate --fake-initial
# ou supprimer db.sqlite3 et relancer les migrations
rm db.sqlite3
python manage.py migrate
```

#### Problème de fichiers statiques

```bash
# Solution : Recollecte des fichiers statiques
python manage.py collectstatic --clear --noinput
```

#### Erreur d'importation CI/CD

- Vérifiez la validité de votre token d'accès
- Assurez-vous que l'ID du projet/repository est correct
- Vérifiez que l'artifact existe et contient le fichier JSON

#### Performance lente

- Vérifiez les index de base de données
- Considérez l'utilisation de PostgreSQL pour de gros volumes
- Activez le cache Django en production

### Logs et débogage

```bash
# Activer le mode debug
export DEBUG=True
python manage.py runserver

# Vérifier la configuration
python manage.py check
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

- **Issues** : [GitHub Issues](https://github.com/nam-edi/playwright-analyst/issues)
- **Documentation** : Disponible directement dans l'interface de l'application

---

**Développé avec ❤️ par [Damien HOFFMANN](https://github.com/nam-edi)**
