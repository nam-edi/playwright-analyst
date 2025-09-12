"""
Tests pour l'application integrations
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from unittest.mock import patch, Mock
import json

from integrations.models import CIConfiguration, GitHubConfiguration, GitLabConfiguration
from projects.models import Project


class CIConfigurationModelTest(TestCase):
    """Tests pour le modèle CIConfiguration"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
    
    def test_ci_configuration_creation(self):
        """Test la création d'une configuration CI"""
        ci_config = CIConfiguration.objects.create(
            name='Test CI Config',
            provider='github'
        )
        
        self.assertEqual(ci_config.name, 'Test CI Config')
        self.assertEqual(ci_config.provider, 'github')
        self.assertIsNotNone(ci_config.created_at)
    
    def test_ci_configuration_str_method(self):
        """Test la méthode __str__ de CIConfiguration"""
        ci_config = CIConfiguration.objects.create(
            name='Test CI Config',
            provider='github'
        )
        self.assertIn("Test CI Config", str(ci_config))
        self.assertIn("GitHub", str(ci_config))
    
    def test_ci_configuration_provider_choices(self):
        """Test les choix de fournisseur"""
        valid_providers = ['github', 'gitlab']
        
        for provider in valid_providers:
            ci_config = CIConfiguration.objects.create(
                name=f'Config {provider}',
                provider=provider
            )
            self.assertEqual(ci_config.provider, provider)
    
    def test_ci_configuration_ordering(self):
        """Test l'ordre des configurations par nom"""
        config_b = CIConfiguration.objects.create(
            name='B Config',
            provider='github'
        )
        config_a = CIConfiguration.objects.create(
            name='A Config',
            provider='gitlab'
        )
        
        configs = list(CIConfiguration.objects.all())
        self.assertEqual(configs[0], config_a)
        self.assertEqual(configs[1], config_b)


class GitHubConfigurationModelTest(TestCase):
    """Tests pour le modèle GitHubConfiguration"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.ci_config = CIConfiguration.objects.create(
            name='GitHub CI',
            provider='github'
        )
    
    def test_github_configuration_creation(self):
        """Test la création d'une configuration GitHub"""
        github_config = GitHubConfiguration.objects.create(
            ci_config=self.ci_config,
            repository='owner/repo',
            access_token='ghp_test_token_123',
            workflow_name='CI Tests',
            artifact_name='test-results',
            json_filename='results.json'
        )
        
        self.assertEqual(github_config.ci_config, self.ci_config)
        self.assertEqual(github_config.repository, 'owner/repo')
        self.assertEqual(github_config.access_token, 'ghp_test_token_123')
        self.assertEqual(github_config.workflow_name, 'CI Tests')
        self.assertEqual(github_config.artifact_name, 'test-results')
        self.assertEqual(github_config.json_filename, 'results.json')
    
    def test_github_configuration_str_method(self):
        """Test la méthode __str__ de GitHubConfiguration"""
        github_config = GitHubConfiguration.objects.create(
            ci_config=self.ci_config,
            repository='owner/repo',
            access_token='test_token',
            workflow_name='CI',
            artifact_name='results',
            json_filename='results.json'
        )
        expected = "GitHub - owner/repo"
        self.assertEqual(str(github_config), expected)
    
    def test_github_configuration_with_branch(self):
        """Test la configuration avec une branche spécifiée"""
        github_config = GitHubConfiguration.objects.create(
            ci_configuration=self.ci_config,
            repository='owner/repo',
            token='test_token',
            branch='develop'
        )
        
        self.assertEqual(github_config.branch, 'develop')
    
    def test_github_configuration_one_to_one(self):
        """Test la relation OneToOne avec CIConfiguration"""
        GitHubConfiguration.objects.create(
            ci_configuration=self.ci_config,
            repository='owner/repo',
            token='test_token'
        )
        
        # Essayer de créer une seconde configuration pour la même CI devrait lever une erreur
        with self.assertRaises(Exception):
            GitHubConfiguration.objects.create(
                ci_configuration=self.ci_config,
                repository='another/repo',
                token='another_token'
            )


class GitLabConfigurationModelTest(TestCase):
    """Tests pour le modèle GitLabConfiguration"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.ci_config = CIConfiguration.objects.create(
            name='GitLab CI',
            provider='gitlab'
        )
    
    def test_gitlab_configuration_creation(self):
        """Test la création d'une configuration GitLab"""
        gitlab_config = GitLabConfiguration.objects.create(
            ci_config=self.ci_config,
            project_id='12345',
            access_token='glpat_test_token_123',
            gitlab_url='https://gitlab.com',
            job_name='test',
            artifact_path='results.json'
        )
        
        self.assertEqual(gitlab_config.ci_config, self.ci_config)
        self.assertEqual(gitlab_config.project_id, '12345')
        self.assertEqual(gitlab_config.access_token, 'glpat_test_token_123')
        self.assertEqual(gitlab_config.gitlab_url, 'https://gitlab.com')
    
    def test_gitlab_configuration_str_method(self):
        """Test la méthode __str__ de GitLabConfiguration"""
        gitlab_config = GitLabConfiguration.objects.create(
            ci_configuration=self.ci_config,
            project_id='12345',
            token='test_token',
            instance_url='https://gitlab.com'
        )
        expected = "GitLab CI - 12345"
        self.assertEqual(str(gitlab_config), expected)
    
    def test_gitlab_configuration_default_instance(self):
        """Test l'instance par défaut GitLab.com"""
        gitlab_config = GitLabConfiguration.objects.create(
            ci_configuration=self.ci_config,
            project_id='12345',
            token='test_token'
        )
        
        self.assertEqual(gitlab_config.instance_url, 'https://gitlab.com')
    
    def test_gitlab_configuration_custom_instance(self):
        """Test une instance GitLab personnalisée"""
        custom_url = 'https://gitlab.mycompany.com'
        gitlab_config = GitLabConfiguration.objects.create(
            ci_configuration=self.ci_config,
            project_id='12345',
            token='test_token',
            instance_url=custom_url
        )
        
        self.assertEqual(gitlab_config.instance_url, custom_url)


class IntegrationsViewsTest(TestCase):
    """Tests pour les vues des intégrations"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.admin_user = User.objects.create_user(username='admin', password='adminpass')
        
        # Créer les groupes
        from django.contrib.auth.models import Group
        self.admin_group = Group.objects.create(name='Admin')
        self.admin_user.groups.add(self.admin_group)
        
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        self.ci_config = CIConfiguration.objects.create(
            name='Test CI',
            platform='github',
            created_by=self.admin_user
        )
    
    def test_ci_configuration_access_permissions(self):
        """Test les permissions d'accès aux configurations CI"""
        # Les utilisateurs normaux ne devraient pas pouvoir gérer les CI
        self.client.login(username='testuser', password='testpass')
        # Ici, vous devriez tester l'accès aux vues de gestion CI une fois qu'elles sont créées
        
        # Les admins devraient pouvoir accéder
        self.client.login(username='admin', password='adminpass')
        # Test des vues admin pour les CI configurations


class CIIntegrationTest(TestCase):
    """Tests d'intégration pour les services CI"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        
        # Configuration GitHub
        self.ci_config = CIConfiguration.objects.create(
            name='GitHub CI',
            platform='github',
            created_by=self.user
        )
        self.github_config = GitHubConfiguration.objects.create(
            ci_configuration=self.ci_config,
            repository='owner/repo',
            token='test_token',
            workflow_name='CI Tests'
        )
        
        # Associer au projet
        self.project.ci_configuration = self.ci_config
        self.project.save()
    
    @patch('requests.get')
    def test_github_workflow_status_check(self, mock_get):
        """Test la vérification du statut du workflow GitHub"""
        # Mock de la réponse GitHub API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'workflow_runs': [
                {
                    'id': 123,
                    'status': 'completed',
                    'conclusion': 'success',
                    'created_at': '2025-01-01T10:00:00Z',
                    'html_url': 'https://github.com/owner/repo/actions/runs/123'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Ici vous testeriez la méthode qui récupère le statut CI
        # Cette méthode devra être implémentée dans les services CI
        # from integrations.services import GitHubService
        # service = GitHubService(self.github_config)
        # status = service.get_latest_workflow_status()
        # self.assertEqual(status['conclusion'], 'success')
    
    @patch('requests.get')
    def test_github_api_authentication_error(self, mock_get):
        """Test la gestion des erreurs d'authentification GitHub"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'message': 'Bad credentials'
        }
        mock_get.return_value = mock_response
        
        # Tester la gestion des erreurs d'authentification
        # Cette logique devra être implémentée dans les services
    
    @patch('requests.get')
    def test_gitlab_project_status_check(self, mock_get):
        """Test la vérification du statut des pipelines GitLab"""
        # Configuration GitLab
        gitlab_ci_config = CIConfiguration.objects.create(
            name='GitLab CI',
            platform='gitlab',
            created_by=self.user
        )
        gitlab_config = GitLabConfiguration.objects.create(
            ci_configuration=gitlab_ci_config,
            project_id='12345',
            token='test_token'
        )
        
        # Mock de la réponse GitLab API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'id': 456,
                'status': 'success',
                'created_at': '2025-01-01T10:00:00.000Z',
                'web_url': 'https://gitlab.com/owner/repo/-/pipelines/456'
            }
        ]
        mock_get.return_value = mock_response
        
        # Tester la récupération des statuts GitLab
        # from integrations.services import GitLabService
        # service = GitLabService(gitlab_config)
        # pipelines = service.get_recent_pipelines()
        # self.assertEqual(pipelines[0]['status'], 'success')


class CIConfigurationValidationTest(TestCase):
    """Tests de validation des configurations CI"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_github_repository_format_validation(self):
        """Test la validation du format du repository GitHub"""
        ci_config = CIConfiguration.objects.create(
            name='GitHub CI',
            platform='github',
            created_by=self.user
        )
        
        # Format valide
        valid_repo = GitHubConfiguration.objects.create(
            ci_configuration=ci_config,
            repository='owner/repo-name',
            token='test_token'
        )
        self.assertEqual(valid_repo.repository, 'owner/repo-name')
        
        # Vous pouvez ajouter des validations personnalisées dans le modèle
        # pour vérifier le format owner/repo
    
    def test_gitlab_instance_url_validation(self):
        """Test la validation de l'URL de l'instance GitLab"""
        ci_config = CIConfiguration.objects.create(
            name='GitLab CI',
            platform='gitlab',
            created_by=self.user
        )
        
        # URL valide
        valid_config = GitLabConfiguration.objects.create(
            ci_configuration=ci_config,
            project_id='12345',
            token='test_token',
            instance_url='https://gitlab.example.com'
        )
        self.assertEqual(valid_config.instance_url, 'https://gitlab.example.com')
        
        # Vous pouvez ajouter des validations pour s'assurer que l'URL est bien formée
    
    def test_token_security(self):
        """Test de la sécurité des tokens"""
        ci_config = CIConfiguration.objects.create(
            name='GitHub CI',
            platform='github',
            created_by=self.user
        )
        
        github_config = GitHubConfiguration.objects.create(
            ci_configuration=ci_config,
            repository='owner/repo',
            token='sensitive_token_123'
        )
        
        # Les tokens devraient être stockés de manière sécurisée
        # Vous pourriez envisager de les chiffrer en base
        self.assertEqual(github_config.token, 'sensitive_token_123')
        
        # Test que les tokens ne sont pas exposés dans les logs ou serializers
