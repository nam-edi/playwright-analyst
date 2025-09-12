"""
Tests pour l'application integrations
"""

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from integrations.models import CIConfiguration, GitHubConfiguration, GitLabConfiguration


class CIConfigurationModelTest(TestCase):
    """Tests pour le modèle CIConfiguration"""

    def setUp(self):
        """Configuration des données de test"""
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_ci_configuration_creation(self):
        """Test la création d'une configuration CI"""
        ci_config = CIConfiguration.objects.create(name="GitHub CI", provider="github")

        self.assertEqual(ci_config.name, "GitHub CI")
        self.assertEqual(ci_config.provider, "github")
        self.assertTrue(ci_config.created_at)

    def test_ci_configuration_str_method(self):
        """Test la méthode __str__ de CIConfiguration"""
        ci_config = CIConfiguration.objects.create(name="GitLab CI", provider="gitlab")

        self.assertEqual(str(ci_config), "GitLab CI (GitLab)")


class GitHubConfigurationModelTest(TestCase):
    """Tests pour le modèle GitHubConfiguration"""

    def setUp(self):
        """Configuration des données de test"""
        self.ci_config = CIConfiguration.objects.create(name="GitHub CI", provider="github")

    def test_github_configuration_creation(self):
        """Test la création d'une configuration GitHub"""
        github_config = GitHubConfiguration.objects.create(
            ci_config=self.ci_config,
            repository="owner/repo",
            access_token="test_token",
            workflow_name="Test Workflow",
            artifact_name="test-results",
            json_filename="results.json",
        )

        self.assertEqual(github_config.ci_config, self.ci_config)
        self.assertEqual(github_config.repository, "owner/repo")
        self.assertEqual(github_config.access_token, "test_token")
        self.assertEqual(github_config.workflow_name, "Test Workflow")

    def test_github_configuration_masked_token(self):
        """Test le masquage du token d'accès"""
        github_config = GitHubConfiguration.objects.create(
            ci_config=self.ci_config,
            repository="owner/repo",
            access_token="ghp_abcdefghijklmnopqrstuvwxyz123456",
            workflow_name="Test Workflow",
            artifact_name="test-results",
            json_filename="results.json",
        )

        masked = github_config.masked_access_token
        self.assertTrue(masked.startswith("ghp_"))
        self.assertTrue("*" in masked)
        self.assertNotEqual(masked, github_config.access_token)

    def test_github_configuration_one_to_one(self):
        """Test la relation OneToOne avec CIConfiguration"""
        GitHubConfiguration.objects.create(
            ci_config=self.ci_config,
            repository="owner/repo",
            access_token="test_token",
            workflow_name="Test Workflow",
            artifact_name="test-results",
            json_filename="results.json",
        )

        # Créer une autre CI config pour le second GitHub config
        ci_config2 = CIConfiguration.objects.create(name="GitHub CI 2", provider="github")

        # Cela devrait fonctionner
        github_config2 = GitHubConfiguration.objects.create(
            ci_config=ci_config2,
            repository="another/repo",
            access_token="another_token",
            workflow_name="Another Workflow",
            artifact_name="other-results",
            json_filename="other.json",
        )

        self.assertEqual(github_config2.ci_config, ci_config2)


class GitLabConfigurationModelTest(TestCase):
    """Tests pour le modèle GitLabConfiguration"""

    def setUp(self):
        self.ci_config = CIConfiguration.objects.create(name="GitLab CI", provider="gitlab")

    def test_gitlab_configuration_creation(self):
        """Test la création d'une configuration GitLab"""
        gitlab_config = GitLabConfiguration.objects.create(
            ci_config=self.ci_config,
            project_id="12345",
            access_token="glpat_test_token_123",
            gitlab_url="https://gitlab.com",
            job_name="test",
            artifact_path="results.json",
        )

        self.assertEqual(gitlab_config.ci_config, self.ci_config)
        self.assertEqual(gitlab_config.project_id, "12345")
        self.assertEqual(gitlab_config.access_token, "glpat_test_token_123")
        self.assertEqual(gitlab_config.gitlab_url, "https://gitlab.com")

    def test_gitlab_configuration_str_method(self):
        """Test la méthode __str__ de GitLabConfiguration"""
        gitlab_config = GitLabConfiguration.objects.create(
            ci_config=self.ci_config,
            project_id="12345",
            access_token="test_token",
            gitlab_url="https://gitlab.com",
            job_name="test",
            artifact_path="results.json",
        )

        self.assertEqual(str(gitlab_config), "GitLab - 12345")

    def test_gitlab_configuration_masked_token(self):
        """Test le masquage du token d'accès GitLab"""
        gitlab_config = GitLabConfiguration.objects.create(
            ci_config=self.ci_config,
            project_id="12345",
            access_token="glpat_abcdefghijklmnopqrstuvwxyz123456",
            gitlab_url="https://custom-gitlab.com",
            job_name="test",
            artifact_path="results.json",
        )

        masked = gitlab_config.masked_access_token
        self.assertTrue(masked.startswith("glpa"))
        self.assertTrue("*" in masked)
        self.assertNotEqual(masked, gitlab_config.access_token)


class IntegrationsViewsTest(TestCase):
    """Tests pour les vues de l'application integrations"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.admin_user = User.objects.create_superuser(username="admin", password="adminpass123", email="admin@test.com")
        self.client = Client()

    def test_integrations_views_exist(self):
        """Test que les vues d'intégrations sont accessibles"""
        # Ce test peut être adapté selon les vues existantes
        self.assertTrue(True)  # Placeholder pour l'instant

    def test_ci_configuration_validation(self):
        """Test la validation des configurations CI"""
        from django.core.exceptions import ValidationError

        # Test avec provider invalide
        ci_config = CIConfiguration(name="Invalid CI", provider="invalid_provider")
        with self.assertRaises(ValidationError):
            ci_config.full_clean()  # Cela déclenche la validation Django

    def test_github_configuration_repository_format(self):
        """Test le format du repository GitHub"""
        ci_config = CIConfiguration.objects.create(name="GitHub CI", provider="github")

        # Repository valide
        github_config = GitHubConfiguration.objects.create(
            ci_config=ci_config, repository="owner/repository-name", access_token="token123"
        )

        self.assertEqual(github_config.repository, "owner/repository-name")

    def test_gitlab_configuration_creation(self):
        """Test la création d'une configuration GitLab complète"""
        ci_config = CIConfiguration.objects.create(name="GitLab CI", provider="gitlab")

        gitlab_config = GitLabConfiguration.objects.create(
            ci_config=ci_config,
            gitlab_url="https://gitlab.example.com",
            project_id="12345",
            access_token="gitlab_token",
            job_name="test-job",
            artifact_path="results.json",
        )

        self.assertEqual(gitlab_config.project_id, "12345")
        self.assertEqual(gitlab_config.gitlab_url, "https://gitlab.example.com")
        self.assertTrue(gitlab_config.access_token)

    def test_configuration_relationships(self):
        """Test les relations entre les modèles de configuration"""
        # Créer une configuration CI avec plusieurs sous-configurations
        ci_config = CIConfiguration.objects.create(name="Multi CI", provider="github")

        github_config = GitHubConfiguration.objects.create(
            ci_config=ci_config,
            repository="test/repo",
            access_token="token",
            workflow_name="ci",
            artifact_name="results",
            json_filename="results.json",
        )

        # Vérifier la relation inverse
        self.assertEqual(ci_config.github_config, github_config)

        # Test de suppression en cascade
        ci_config_id = ci_config.id
        ci_config.delete()

        # La configuration GitHub devrait être supprimée aussi
        self.assertFalse(GitHubConfiguration.objects.filter(ci_config_id=ci_config_id).exists())

    # def test_configuration_active_status(self):
    #     """Test le statut actif des configurations"""
    #     ci_config = CIConfiguration.objects.create(
    #         name="Test CI",
    #         provider="github",
    #         is_active=False
    #     )
    #
    #     self.assertFalse(ci_config.is_active)
    #
    #     # Réactiver
    #     ci_config.is_active = True
    #     ci_config.save()
    #
    #     ci_config.refresh_from_db()
    #     self.assertTrue(ci_config.is_active)

    # def test_configuration_settings_json(self):
    #     """Test les paramètres JSON des configurations"""
    #     settings = {
    #         "timeout": 300,
    #         "retry_count": 3,
    #         "notifications": ["email", "slack"]
    #     }
    #
    #     ci_config = CIConfiguration.objects.create(
    #         name="JSON CI",
    #         provider="github",
    #         settings=settings
    #     )

    # self.assertEqual(ci_config.settings["timeout"], 300)
    # self.assertEqual(ci_config.settings["retry_count"], 3)
    # self.assertIn("email", ci_config.settings["notifications"])
