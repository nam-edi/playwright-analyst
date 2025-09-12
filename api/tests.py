"""
Tests pour l'application api
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import json
import secrets

from api.models import APIKey
from projects.models import Project
from testing.models import TestExecution, Test, TestResult


class APIKeyModelTest(TestCase):
    """Tests pour le modèle APIKey"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
    
    def test_api_key_creation(self):
        """Test la création d'une clé API"""
        api_key = APIKey.objects.create(
            name='Test API Key',
            user=self.user
        )
        
        self.assertEqual(api_key.name, 'Test API Key')
        self.assertEqual(api_key.user, self.user)
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)
        self.assertTrue(api_key.is_active)
        self.assertIsNotNone(api_key.key)
        self.assertIsNotNone(api_key.created_at)
    
    def test_api_key_auto_generation(self):
        """Test la génération automatique de la clé"""
        api_key = APIKey.objects.create(
            name='Test API Key',
            user=self.user
        )
        
        # La clé devrait être générée automatiquement
        self.assertIsNotNone(api_key.key)
        self.assertEqual(len(api_key.key), 43)  # secrets.token_urlsafe(32) génère 43 caractères
    
    def test_api_key_manual_key(self):
        """Test la création avec une clé manuelle"""
        manual_key = 'manual-test-key-123'
        api_key = APIKey.objects.create(
            name='Test API Key',
            user=self.user,
            key=manual_key
        )
        
        self.assertEqual(api_key.key, manual_key)
    
    def test_api_key_str_method(self):
        """Test la méthode __str__ de l'APIKey"""
        api_key = APIKey.objects.create(
            name='Test API Key',
            user=self.user
        )
        expected = f"Test API Key ({self.user.username})"
        self.assertEqual(str(api_key), expected)
    
    def test_api_key_unique_constraint(self):
        """Test la contrainte d'unicité de la clé"""
        key = 'unique-test-key'
        APIKey.objects.create(
            name='First Key',
            user=self.user,
            key=key
        )
        
        # Créer une seconde clé avec la même valeur devrait lever une erreur
        with self.assertRaises(Exception):
            APIKey.objects.create(
                name='Second Key',
                user=self.user,
                key=key
            )
    
    def test_api_key_expiration(self):
        """Test la propriété is_expired"""
        # Clé sans expiration
        api_key_permanent = APIKey.objects.create(
            name='Permanent Key',
            user=self.user
        )
        self.assertFalse(api_key_permanent.is_expired)
        
        # Clé expirée
        api_key_expired = APIKey.objects.create(
            name='Expired Key',
            user=self.user,
            expires_at=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(api_key_expired.is_expired)
        
        # Clé future
        api_key_future = APIKey.objects.create(
            name='Future Key',
            user=self.user,
            expires_at=timezone.now() + timedelta(days=1)
        )
        self.assertFalse(api_key_future.is_expired)
    
    def test_api_key_projects_relationship(self):
        """Test la relation avec les projets"""
        api_key = APIKey.objects.create(
            name='Test API Key',
            user=self.user
        )
        
        # Sans projets spécifiés - accès à tous les projets
        self.assertEqual(api_key.projects.count(), 0)
        
        # Avec projets spécifiques
        project2 = Project.objects.create(name='Another Project', created_by=self.user)
        api_key.projects.add(self.project, project2)
        
        self.assertEqual(api_key.projects.count(), 2)
        self.assertIn(self.project, api_key.projects.all())
        self.assertIn(project2, api_key.projects.all())
    
    def test_api_key_permissions(self):
        """Test les permissions de la clé API"""
        # Clé avec permissions par défaut
        api_key = APIKey.objects.create(
            name='Default Key',
            user=self.user
        )
        self.assertTrue(api_key.can_upload)
        self.assertTrue(api_key.can_read)
        
        # Clé en lecture seule
        readonly_key = APIKey.objects.create(
            name='Read Only Key',
            user=self.user,
            can_upload=False,
            can_read=True
        )
        self.assertFalse(readonly_key.can_upload)
        self.assertTrue(readonly_key.can_read)


class APIViewsTest(TestCase):
    """Tests pour les vues API"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        
        self.api_key = APIKey.objects.create(
            name='Test API Key',
            user=self.user,
            key='test-api-key-123'
        )
        self.api_key.projects.add(self.project)
    
    def test_api_documentation_view(self):
        """Test la vue de documentation API"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('api_documentation'))
        self.assertEqual(response.status_code, 200)
    
    def test_api_key_help_view(self):
        """Test la vue d'aide pour les clés API"""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('api_key_help'))
        self.assertEqual(response.status_code, 200)
    
    def test_api_upload_without_key(self):
        """Test l'upload sans clé API"""
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(url, {}, content_type='application/json')
        self.assertEqual(response.status_code, 401)  # Unauthorized
    
    def test_api_upload_with_invalid_key(self):
        """Test l'upload avec clé API invalide"""
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(
            url, 
            {}, 
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer invalid-key'
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized
    
    def test_api_upload_with_valid_key_no_permission(self):
        """Test l'upload avec clé valide mais sans permission d'upload"""
        readonly_key = APIKey.objects.create(
            name='Read Only Key',
            user=self.user,
            key='readonly-key-123',
            can_upload=False,
            can_read=True
        )
        readonly_key.projects.add(self.project)
        
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(
            url,
            {},
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer readonly-key-123'
        )
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_api_upload_expired_key(self):
        """Test l'upload avec clé expirée"""
        expired_key = APIKey.objects.create(
            name='Expired Key',
            user=self.user,
            key='expired-key-123',
            expires_at=timezone.now() - timedelta(days=1)
        )
        expired_key.projects.add(self.project)
        
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(
            url,
            {},
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer expired-key-123'
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized
    
    def test_api_upload_inactive_key(self):
        """Test l'upload avec clé inactive"""
        inactive_key = APIKey.objects.create(
            name='Inactive Key',
            user=self.user,
            key='inactive-key-123',
            is_active=False
        )
        inactive_key.projects.add(self.project)
        
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(
            url,
            {},
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer inactive-key-123'
        )
        self.assertEqual(response.status_code, 401)  # Unauthorized
    
    def test_api_upload_project_not_authorized(self):
        """Test l'upload sur un projet non autorisé"""
        unauthorized_project = Project.objects.create(
            name='Unauthorized Project',
            created_by=self.user
        )
        
        url = reverse('api_upload_results', kwargs={'project_id': unauthorized_project.id})
        response = self.client.post(
            url,
            {},
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test-api-key-123'
        )
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_api_upload_valid_request(self):
        """Test un upload valide via API"""
        # Créer des données de test valides
        test_data = {
            "execution": {
                "name": "API Test Execution",
                "browser": "chromium",
                "environment": "test"
            },
            "results": [
                {
                    "test_name": "API Test Case",
                    "file_path": "tests/api.spec.js",
                    "status": "passed",
                    "duration": 1500.0,
                    "error_message": None
                }
            ]
        }
        
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(
            url,
            json.dumps(test_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test-api-key-123'
        )
        
        # Devrait créer l'exécution et les résultats
        self.assertEqual(response.status_code, 201)  # Created
        
        # Vérifier que les données ont été créées
        self.assertTrue(TestExecution.objects.filter(name="API Test Execution").exists())
        self.assertTrue(Test.objects.filter(name="API Test Case").exists())
        self.assertTrue(TestResult.objects.filter(status="passed").exists())
        
        # Vérifier que last_used a été mis à jour
        self.api_key.refresh_from_db()
        self.assertIsNotNone(self.api_key.last_used)
    
    def test_api_upload_malformed_json(self):
        """Test l'upload avec JSON malformé"""
        url = reverse('api_upload_results', kwargs={'project_id': self.project.id})
        response = self.client.post(
            url,
            "invalid json",
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer test-api-key-123'
        )
        self.assertEqual(response.status_code, 400)  # Bad Request
    
    def test_api_key_all_projects_access(self):
        """Test l'accès à tous les projets quand aucun projet spécifique n'est assigné"""
        # Clé sans projets spécifiés
        universal_key = APIKey.objects.create(
            name='Universal Key',
            user=self.user,
            key='universal-key-123'
        )
        # Ne pas ajouter de projets spécifiques
        
        # Créer un autre projet
        another_project = Project.objects.create(name='Another Project', created_by=self.user)
        
        # Devrait pouvoir uploader sur n'importe quel projet
        url = reverse('api_upload_results', kwargs={'project_id': another_project.id})
        test_data = {
            "execution": {
                "name": "Universal Test",
                "browser": "firefox"
            },
            "results": []
        }
        
        response = self.client.post(
            url,
            json.dumps(test_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer universal-key-123'
        )
        
        self.assertEqual(response.status_code, 201)  # Created
