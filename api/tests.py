# Tests pour l'application API

import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from api.models import APIKey
from projects.models import Project
from testing.models import TestExecution


class APIKeyModelTest(TestCase):
    """Tests pour le modèle APIKey"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_api_key_creation(self):
        """Test la création d'une clé API"""
        api_key = APIKey.objects.create(name="Test API Key", user=self.user)

        self.assertEqual(api_key.name, "Test API Key")
        self.assertEqual(api_key.user, self.user)
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)
        self.assertTrue(api_key.is_active)
        self.assertIsNotNone(api_key.key)
        self.assertIsNotNone(api_key.created_at)

    def test_api_key_auto_generation(self):
        """Test la génération automatique de la clé"""
        api_key = APIKey.objects.create(name="Test API Key", user=self.user)

        # La clé devrait être générée automatiquement
        self.assertIsNotNone(api_key.key)
        self.assertEqual(len(api_key.key), 43)  # secrets.token_urlsafe(32) génère 43 caractères

    def test_api_key_manual_key(self):
        """Test la création avec une clé manuelle"""
        manual_key = "manual-test-key-123"
        api_key = APIKey.objects.create(name="Test API Key", user=self.user, key=manual_key)

        self.assertEqual(api_key.key, manual_key)

    def test_api_key_str_method(self):
        """Test la méthode __str__ de l'APIKey"""
        api_key = APIKey.objects.create(name="Test API Key", user=self.user)
        expected = f"Test API Key ({self.user.username})"
        self.assertEqual(str(api_key), expected)

    def test_api_key_unique_constraint(self):
        """Test la contrainte d'unicité de la clé"""
        key = "unique-test-key"
        APIKey.objects.create(name="First Key", user=self.user, key=key)

        # Créer une seconde clé avec la même valeur devrait lever une erreur
        with self.assertRaises(Exception):
            APIKey.objects.create(name="Second Key", user=self.user, key=key)

    def test_api_key_expiration(self):
        """Test la propriété is_expired"""
        # Clé sans expiration
        api_key_permanent = APIKey.objects.create(name="Permanent Key", user=self.user)
        self.assertFalse(api_key_permanent.is_expired)

        # Clé expirée
        api_key_expired = APIKey.objects.create(
            name="Expired Key", user=self.user, expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(api_key_expired.is_expired)

        # Clé future
        api_key_future = APIKey.objects.create(
            name="Future Key", user=self.user, expires_at=timezone.now() + timedelta(days=1)
        )
        self.assertFalse(api_key_future.is_expired)

    def test_api_key_projects_relationship(self):
        """Test la relation avec les projets"""
        api_key = APIKey.objects.create(name="Test API Key", user=self.user)

        # Sans projets spécifiés - accès à tous les projets
        self.assertEqual(api_key.projects.count(), 0)

        # Avec projets spécifiques
        project2 = Project.objects.create(name="Another Project", created_by=self.user)
        api_key.projects.add(self.project, project2)

        self.assertEqual(api_key.projects.count(), 2)
        self.assertIn(self.project, api_key.projects.all())
        self.assertIn(project2, api_key.projects.all())

    def test_api_key_permissions(self):
        """Test les permissions de la clé API"""
        # Clé avec permissions par défaut
        api_key = APIKey.objects.create(name="Default Key", user=self.user)
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)

        # Clé en lecture seule
        readonly_key = APIKey.objects.create(name="Read Only Key", user=self.user, can_upload=False, can_read=True)
        self.assertFalse(readonly_key.can_upload)
        self.assertTrue(readonly_key.can_read)


class APIViewsTest(TestCase):
    """Tests pour les vues API"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

        self.api_key = APIKey.objects.create(name="Test API Key", user=self.user, key="test-api-key-123")
        self.api_key.projects.add(self.project)

    def get_valid_json_data(self):
        """Retourne des données JSON valides pour les tests d'upload"""
        return {
            "suites": [],
            "stats": {
                "startTime": "2025-01-01T10:00:00.000Z",
                "duration": 0,
                "expected": 0,
                "skipped": 0,
                "unexpected": 0,
                "flaky": 0,
            },
            "config": {"configFile": "", "rootDir": "", "version": "1.0.0", "workers": 1, "metadata": {"actualWorkers": 1}},
        }

    def test_api_documentation_view(self):
        """Test la vue de documentation API"""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("api:documentation"))
        self.assertEqual(response.status_code, 200)

    def test_api_key_help_view(self):
        """Test la vue d'aide pour les clés API"""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("api:key_help"))
        self.assertEqual(response.status_code, 200)

    def test_api_upload_without_key(self):
        """Test l'upload sans clé API"""
        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        data = self.get_valid_json_data()
        response = self.client.post(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 201)  # Created (pas d'authentification pour l'instant)

    def test_api_upload_with_invalid_key(self):
        """Test l'upload avec clé API invalide"""
        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Structure JSON valide
            content_type="application/json",
            HTTP_X_API_KEY="invalid-key-123",
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_api_upload_with_valid_key_no_permission(self):
        """Test l'upload avec clé valide mais sans permission d'upload"""
        readonly_key = APIKey.objects.create(
            name="Read Only Key", user=self.user, key="readonly-key-123", can_upload=False, can_read=True
        )
        readonly_key.projects.add(self.project)

        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Structure JSON valide
            content_type="application/json",
            HTTP_X_API_KEY="readonly-key-123",  # Utiliser X-API-Key comme dans la vue
        )
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_api_upload_expired_key(self):
        """Test l'upload avec clé expirée"""
        expired_key = APIKey.objects.create(
            name="Expired Key", user=self.user, key="expired-key-123", expires_at=timezone.now() - timedelta(days=1)
        )
        expired_key.projects.add(self.project)

        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Structure JSON valide
            content_type="application/json",
            HTTP_X_API_KEY="expired-key-123",  # Utiliser X-API-Key
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_api_upload_inactive_key(self):
        """Test l'upload avec clé inactive"""
        inactive_key = APIKey.objects.create(name="Inactive Key", user=self.user, key="inactive-key-123", is_active=False)
        inactive_key.projects.add(self.project)

        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Structure JSON valide
            content_type="application/json",
            HTTP_X_API_KEY="inactive-key-123",  # Utiliser X-API-Key
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized

    def test_api_upload_project_not_authorized(self):
        """Test l'upload sur un projet non autorisé"""
        unauthorized_project = Project.objects.create(name="Unauthorized Project", created_by=self.user)

        url = reverse("api:upload_results", kwargs={"project_id": unauthorized_project.id})
        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Structure JSON valide
            content_type="application/json",
            HTTP_X_API_KEY="test-api-key-123",  # Utiliser X-API-Key
        )
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_api_upload_valid_request(self):
        """Test un upload valide via API"""
        # Créer des données de test valides
        _ = {
            "execution": {"name": "API Test Execution", "browser": "chromium", "environment": "test"},
            "results": [
                {
                    "test_name": "API Test Case",
                    "file_path": "tests/api.spec.js",
                    "status": "passed",
                    "duration": 1500.0,
                    "error_message": None,
                }
            ],
        }

        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Pour l'instant, utilisons la structure minimale attendue
            content_type="application/json",
            HTTP_X_API_KEY="test-api-key-123",  # Utiliser X-API-Key
        )

        # Devrait créer l'exécution et les résultats
        self.assertEqual(response.status_code, 201)  # Created

        # Vérifier que l'exécution a été créée
        self.assertTrue(TestExecution.objects.filter(project=self.project).exists())

        # Vérifier que last_used a été mis à jour
        self.api_key.refresh_from_db()
        self.assertIsNotNone(self.api_key.last_used)

    def test_api_upload_malformed_json(self):
        """Test l'upload avec JSON malformé"""
        url = reverse("api:upload_results", kwargs={"project_id": self.project.id})
        response = self.client.post(
            url, "invalid json", content_type="application/json", HTTP_X_API_KEY="test-api-key-123"  # Utiliser X-API-Key
        )
        self.assertEqual(response.status_code, 400)  # Bad Request

    def test_api_key_all_projects_access(self):
        """Test l'accès à tous les projets quand aucun projet spécifique n'est assigné"""
        # Clé sans projets spécifiés
        _ = APIKey.objects.create(name="Universal Key", user=self.user, key="universal-key-123")
        # Ne pas ajouter de projets spécifiques

        # Créer un autre projet
        another_project = Project.objects.create(name="Another Project", created_by=self.user)

        # Devrait pouvoir uploader sur n'importe quel projet
        url = reverse("api:upload_results", kwargs={"project_id": another_project.id})
        _ = {"execution": {"name": "Universal Test", "browser": "firefox"}, "results": []}

        response = self.client.post(
            url,
            json.dumps(self.get_valid_json_data()),  # Structure minimale attendue
            content_type="application/json",
            HTTP_X_API_KEY="universal-key-123",  # Utiliser X-API-Key
        )

        self.assertEqual(response.status_code, 201)  # Created


class APIKeyAdditionalTest(TestCase):
    """Tests additionnels pour APIKey pour améliorer la couverture"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_api_key_str_method(self):
        """Test la méthode __str__ d'APIKey"""
        api_key = APIKey.objects.create(name="Test Key", user=self.user)
        expected = f"Test Key ({self.user.username})"
        self.assertEqual(str(api_key), expected)

    def test_api_key_properties(self):
        """Test des propriétés de l'APIKey"""
        # Clé non expirée
        api_key = APIKey.objects.create(name="Test Key", user=self.user)
        self.assertFalse(api_key.is_expired)

        # Clé expirée
        api_key_expired = APIKey.objects.create(
            name="Expired Key", user=self.user, expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(api_key_expired.is_expired)

    def test_api_key_permissions_variations(self):
        """Test les permissions des clés API"""
        # Clé avec permissions par défaut
        api_key = APIKey.objects.create(name="Default Key", user=self.user)
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)
        self.assertTrue(api_key.is_active)

        # Clé en lecture seule
        readonly_key = APIKey.objects.create(name="ReadOnly Key", user=self.user, can_upload=False, can_read=True)
        self.assertFalse(readonly_key.can_upload)
        self.assertTrue(readonly_key.can_read)

        # Clé inactive
        inactive_key = APIKey.objects.create(name="Inactive Key", user=self.user, is_active=False)
        self.assertFalse(inactive_key.is_active)

    def test_api_key_project_relationships(self):
        """Test les relations avec les projets"""
        api_key = APIKey.objects.create(name="Test Key", user=self.user)

        # Sans projets spécifiés - accès à tous
        self.assertEqual(api_key.projects.count(), 0)

        # Avec projets spécifiques
        project2 = Project.objects.create(name="Project 2", created_by=self.user)
        api_key.projects.add(self.project, project2)

        self.assertEqual(api_key.projects.count(), 2)
        self.assertIn(self.project, api_key.projects.all())
        self.assertIn(project2, api_key.projects.all())

    def test_api_key_auto_generation(self):
        """Test la génération automatique de la clé"""
        api_key = APIKey.objects.create(name="Auto Key", user=self.user)

        # La clé devrait être générée automatiquement
        self.assertIsNotNone(api_key.key)
        self.assertGreater(len(api_key.key), 10)  # Doit avoir une longueur raisonnable

    def test_api_key_manual_key(self):
        """Test la création avec une clé manuelle"""
        manual_key = "manual-test-key-123"
        api_key = APIKey.objects.create(name="Manual Key", user=self.user, key=manual_key)
        self.assertEqual(api_key.key, manual_key)

    def test_api_key_basic_creation(self):
        """Test création basique d'APIKey avec tous les champs"""
        api_key = APIKey.objects.create(
            name="Complete Key",
            user=self.user,
            can_upload=True,
            can_read=True,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=30),
        )

        self.assertEqual(api_key.name, "Complete Key")
        self.assertEqual(api_key.user, self.user)
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)
        self.assertTrue(api_key.is_active)
        self.assertIsNotNone(api_key.expires_at)
        self.assertIsNotNone(api_key.created_at)


class APIAdminTest(TestCase):
    """Tests pour les classes admin de l'API"""

    def test_api_key_admin_exists(self):
        """Test que APIKeyAdmin existe et a des propriétés de base"""
        from api.admin import APIKeyAdmin

        self.assertIsNotNone(APIKeyAdmin)

        # Vérifier quelques propriétés de base si elles existent
        if hasattr(APIKeyAdmin, "list_display"):
            self.assertIsNotNone(APIKeyAdmin.list_display)
        if hasattr(APIKeyAdmin, "search_fields"):
            self.assertIsNotNone(APIKeyAdmin.search_fields)

    def test_api_apps_config(self):
        """Test de la configuration de l'app API"""
        from api.apps import ApiConfig

        self.assertEqual(ApiConfig.name, "api")
        self.assertIsNotNone(ApiConfig.default_auto_field)


class APIAdditionalCoverageTest(TestCase):
    """Tests supplémentaires pour augmenter la couverture de l'API"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_api_key_creation_extended(self):
        """Test de création de clé API étendu"""
        api_key = APIKey.objects.create(name="Test API Key", user=self.user)
        # Ajouter le projet après création
        api_key.projects.add(self.project)

        self.assertEqual(api_key.name, "Test API Key")
        self.assertEqual(api_key.user, self.user)
        self.assertTrue(api_key.key)  # La clé est générée automatiquement
        self.assertTrue(api_key.projects.filter(id=self.project.id).exists())
        self.assertTrue(api_key.is_active)
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)

    def test_api_key_string_representation(self):
        """Test de la représentation string de l'APIKey"""
        api_key = APIKey.objects.create(name="Test API Key", user=self.user)
        self.assertIsInstance(str(api_key), str)
        self.assertIn("Test API Key", str(api_key))

    def test_api_key_permissions(self):
        """Test des permissions de l'APIKey"""
        api_key = APIKey.objects.create(name="Limited Key", user=self.user, can_upload=False, can_read=True)
        self.assertFalse(api_key.can_upload)
        self.assertTrue(api_key.can_read)

    def test_api_key_inactive(self):
        """Test d'une clé API inactive"""
        api_key = APIKey.objects.create(name="Inactive Key", user=self.user, is_active=False)
        self.assertFalse(api_key.is_active)

    def test_api_key_project_associations(self):
        """Test des associations de projet avec APIKey"""
        api_key = APIKey.objects.create(name="Multi Project Key", user=self.user)

        # Créer un autre projet
        project2 = Project.objects.create(name="Project 2", created_by=self.user)

        # Associer les projets
        api_key.projects.add(self.project, project2)

        self.assertEqual(api_key.projects.count(), 2)
        self.assertTrue(api_key.projects.filter(name="Test Project").exists())
        self.assertTrue(api_key.projects.filter(name="Project 2").exists())

    def test_api_key_model_fields(self):
        """Test des champs du modèle APIKey"""
        api_key = APIKey.objects.create(name="Field Test Key", user=self.user)

        # Vérifier que les champs existent
        self.assertTrue(hasattr(api_key, "name"))
        self.assertTrue(hasattr(api_key, "user"))
        self.assertTrue(hasattr(api_key, "key"))
        self.assertTrue(hasattr(api_key, "created_at"))
        self.assertTrue(hasattr(api_key, "is_active"))
        self.assertTrue(hasattr(api_key, "can_upload"))
        self.assertTrue(hasattr(api_key, "can_read"))
        self.assertTrue(hasattr(api_key, "projects"))

    def test_api_key_queryset_operations(self):
        """Test d'opérations sur les querysets APIKey"""
        # Créer plusieurs clés
        APIKey.objects.create(name="Key 1", user=self.user)
        APIKey.objects.create(name="Key 2", user=self.user, is_active=False)

        # Test count
        total_keys = APIKey.objects.count()
        self.assertTrue(total_keys >= 2)

        # Test filter
        active_keys = APIKey.objects.filter(is_active=True)
        inactive_keys = APIKey.objects.filter(is_active=False)

        self.assertTrue(active_keys.exists())
        self.assertTrue(inactive_keys.exists())

        # Test values
        key_names = APIKey.objects.values_list("name", flat=True)
        self.assertIn("Key 1", key_names)
        self.assertIn("Key 2", key_names)
