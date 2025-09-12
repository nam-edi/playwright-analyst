# 🚀 Configuration CI/CD - Playwright Analyst

Ce répertoire contient la configuration GitHub Actions pour l'intégration et le déploiement continus.

## 📋 Workflows Configurés

### 1. 🧪 `django-tests.yml` - Tests Principaux

**Déclenché sur :** Tous les push + Pull Requests vers main

**Actions :**

- ✅ Tests Django sur Python 3.11, 3.12, 3.13
- 🔍 Vérifications statiques (flake8)
- 🗄️ Validation des migrations
- 📊 Rapport de couverture de code
- 🛡️ Analyse de sécurité (bandit, pip-audit)

### 2. 🔍 `pr-checks.yml` - Vérifications Pull Request

**Déclenché sur :** Pull Requests vers main (non-draft)

**Actions :**

- 📊 Tests avec couverture obligatoire (≥80%)
- 🎨 Vérifications de formatage (Black, isort)
- 🔒 Tests de sécurité stricts
- 📝 Commentaires automatiques sur la PR
- ⚡ Analyse de performance

### 3. 🚀 `deploy-main.yml` - Déploiement Main

**Déclenché sur :** Push sur main

**Actions :**

- 🧪 Tests finaux complets
- 🏷️ Création automatique de tags de version
- 📋 Génération de releases GitHub
- 🎉 Notifications de succès

### 4. 🛡️ `security-check.yml` - Audit de Sécurité

**Déclenché sur :** Quotidien (2h UTC) + changements requirements.txt

**Actions :**

- 🔒 Audit des vulnérabilités (pip-audit, bandit)
- 🔍 Détection de secrets (detect-secrets)
- 📊 Analyse des dépendances
- 🚨 Création d'issues automatiques si problèmes critiques
- 🧹 Nettoyage hebdomadaire

## 🛠️ Configuration Locale

Pour que vos commits passent les vérifications CI, installez les outils localement :

```bash
# Outils de formatage et de vérification
pip install black isort flake8 bandit safety coverage

# Pre-commit hooks (recommandé)
pip install pre-commit
pre-commit install
```

### 🎨 Formatage automatique

```bash
# Formatage du code
black .

# Tri des imports
isort .

# Vérifications
flake8 .
```

### 🧪 Tests locaux

```bash
# Tests avec couverture
coverage run --source='.' manage.py test
coverage report
coverage html  # Génère un rapport HTML

# Tests parallèles (plus rapide)
python manage.py test --parallel
```

### 🛡️ Vérifications de sécurité

```bash
# Analyse de sécurité du code
bandit -r .

# Audit des dépendances
pip-audit

# Recherche de secrets
detect-secrets scan --all-files
```

## 📊 Status Badges

Ajoutez ces badges à votre README principal :

```markdown
![Tests](https://github.com/nam-edi/playwright-analyst/workflows/Django%20Tests/badge.svg)
![Security](https://github.com/nam-edi/playwright-analyst/workflows/Security%20&%20Dependencies%20Check/badge.svg)
![CodeCov](https://codecov.io/gh/nam-edi/playwright-analyst/branch/main/graph/badge.svg)
```

## 🔧 Protection de Branches

Pour main, configurez dans GitHub :

- ☑️ Require pull request reviews
- ☑️ Require status checks to pass before merging
- ☑️ Require branches to be up to date before merging
- ☑️ Include administrators

**Status checks requis :**

- `test (3.13)` - Tests Django
- `required-checks` - Vérifications PR
- `security-audit` - Audit de sécurité

## 📝 Guide de Contribution

### Workflow recommandé :

1. 🌿 **Créer une branche :** `git checkout -b feature/ma-nouvelle-fonctionnalite`

2. 💻 **Développer avec tests :**

   ```bash
   # Écrire des tests
   python manage.py test

   # Vérifier le formatage
   black . && isort . && flake8 .
   ```

3. 📤 **Push et PR :**

   ```bash
   git push origin feature/ma-nouvelle-fonctionnalite
   # Créer la PR sur GitHub
   ```

4. ✅ **Vérifications automatiques :** La CI vérifie automatiquement
5. 🔄 **Review et merge :** Une fois approuvée, merge vers main

6. 🚀 **Déploiement automatique :** La CI déploie automatiquement

## 🆘 Résolution de Problèmes

### ❌ Tests qui échouent

```bash
# Lancer les tests localement avec verbosité
python manage.py test --verbosity=2 --keepdb

# Débugger un test spécifique
python manage.py test core.tests.UserContextModelTest.test_user_context_creation
```

### 🎨 Problèmes de formatage

```bash
# Correction automatique
black .
isort .

# Vérification
flake8 . --count --statistics
```

### 🛡️ Problèmes de sécurité

```bash
# Identifier les problèmes
bandit -r . -ll

# Audit des dépendances
pip-audit --fix

# Mettre à jour les dépendances
pip install --upgrade -r requirements.txt
```

### 🗄️ Problèmes de migrations

```bash
# Vérifier les migrations
python manage.py makemigrations --check --dry-run

# Créer les migrations manquantes
python manage.py makemigrations

# Tester les migrations
python manage.py migrate --run-syncdb
```

## 🔗 Liens Utiles

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Bandit Security Linter](https://bandit.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)

---

Cette configuration garantit que seul du code de qualité et sécurisé atteint la branche main ! 🎯
