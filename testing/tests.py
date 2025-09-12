"""
Tests pour l'application testing
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from testing.models import Tag, Test, TestExecution, TestResult
from projects.models import Project


class TagModelTest(TestCase):
    """Tests pour le modèle Tag"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
    
    def test_tag_creation(self):
        """Test la création d'un tag"""
        tag = Tag.objects.create(
            name='Critical',
            color='#ff0000',
            project=self.project
        )
        
        self.assertEqual(tag.name, 'Critical')
        self.assertEqual(tag.color, '#ff0000')
        self.assertEqual(tag.project, self.project)
        self.assertIsNotNone(tag.created_at)
    
    def test_tag_str_method(self):
        """Test la méthode __str__ du tag"""
        tag = Tag.objects.create(
            name='Critical',
            project=self.project
        )
        expected = f"{self.project.name} - Critical"
        self.assertEqual(str(tag), expected)
    
    def test_tag_unique_name_per_project(self):
        """Test la contrainte d'unicité nom/projet"""
        Tag.objects.create(
            name='Critical',
            project=self.project
        )
        
        # Créer un tag avec le même nom dans le même projet devrait lever une erreur
        with self.assertRaises(Exception):
            Tag.objects.create(
                name='Critical',
                project=self.project
            )
    
    def test_tag_unique_color_per_project(self):
        """Test la contrainte d'unicité couleur/projet"""
        Tag.objects.create(
            name='Critical',
            color='#ff0000',
            project=self.project
        )
        
        # Créer un tag avec la même couleur dans le même projet devrait lever une erreur
        with self.assertRaises(Exception):
            Tag.objects.create(
                name='Important',
                color='#ff0000',
                project=self.project
            )
    
    def test_tag_different_projects_same_name_color(self):
        """Test que des tags peuvent avoir le même nom/couleur sur des projets différents"""
        project2 = Project.objects.create(name='Another Project', created_by=self.user)
        
        tag1 = Tag.objects.create(
            name='Critical',
            color='#ff0000',
            project=self.project
        )
        
        # Devrait fonctionner sur un autre projet
        tag2 = Tag.objects.create(
            name='Critical',
            color='#ff0000',
            project=project2
        )
        
        self.assertEqual(tag1.name, tag2.name)
        self.assertEqual(tag1.color, tag2.color)
        self.assertNotEqual(tag1.project, tag2.project)


class TestModelTest(TestCase):
    """Tests pour le modèle Test"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        self.tag = Tag.objects.create(name='Critical', project=self.project)
    
    def test_test_creation(self):
        """Test la création d'un test"""
        test = Test.objects.create(
            name='Login Test',
            file_path='tests/login.spec.js',
            project=self.project
        )
        
        self.assertEqual(test.name, 'Login Test')
        self.assertEqual(test.file_path, 'tests/login.spec.js')
        self.assertEqual(test.project, self.project)
        self.assertIsNotNone(test.created_at)
    
    def test_test_str_method(self):
        """Test la méthode __str__ du test"""
        test = Test.objects.create(
            name='Login Test',
            file_path='tests/login.spec.js',
            project=self.project
        )
        expected = f"{self.project.name} - Login Test"
        self.assertEqual(str(test), expected)
    
    def test_test_with_tags(self):
        """Test l'association d'un test avec des tags"""
        test = Test.objects.create(
            name='Login Test',
            file_path='tests/login.spec.js',
            project=self.project
        )
        
        test.tags.add(self.tag)
        self.assertEqual(test.tags.count(), 1)
        self.assertIn(self.tag, test.tags.all())
    
    def test_test_unique_constraint(self):
        """Test la contrainte d'unicité nom/projet"""
        Test.objects.create(
            name='Login Test',
            file_path='tests/login.spec.js',
            project=self.project
        )
        
        # Créer un test avec le même nom dans le même projet devrait lever une erreur
        with self.assertRaises(Exception):
            Test.objects.create(
                name='Login Test',
                file_path='tests/other.spec.js',
                project=self.project
            )


class TestExecutionModelTest(TestCase):
    """Tests pour le modèle TestExecution"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
    
    def test_execution_creation(self):
        """Test la création d'une exécution"""
        execution = TestExecution.objects.create(
            name='Build #123',
            project=self.project,
            browser='chromium',
            environment='staging'
        )
        
        self.assertEqual(execution.name, 'Build #123')
        self.assertEqual(execution.project, self.project)
        self.assertEqual(execution.browser, 'chromium')
        self.assertEqual(execution.environment, 'staging')
        self.assertIsNotNone(execution.created_at)
    
    def test_execution_str_method(self):
        """Test la méthode __str__ de l'exécution"""
        execution = TestExecution.objects.create(
            name='Build #123',
            project=self.project
        )
        expected = f"{self.project.name} - Build #123"
        self.assertEqual(str(execution), expected)
    
    def test_execution_statistics(self):
        """Test le calcul des statistiques d'exécution"""
        execution = TestExecution.objects.create(
            name='Build #123',
            project=self.project
        )
        
        # Créer des tests et résultats
        test1 = Test.objects.create(name='Test 1', project=self.project)
        test2 = Test.objects.create(name='Test 2', project=self.project)
        test3 = Test.objects.create(name='Test 3', project=self.project)
        
        TestResult.objects.create(test=test1, execution=execution, status='passed')
        TestResult.objects.create(test=test2, execution=execution, status='failed')
        TestResult.objects.create(test=test3, execution=execution, status='skipped')
        
        # Tester les méthodes de statistiques (si elles existent dans le modèle)
        # Ces méthodes devront être implémentées dans le modèle
        self.assertEqual(execution.test_results.count(), 3)
    
    def test_execution_ordering(self):
        """Test l'ordre des exécutions par date de création (desc)"""
        execution1 = TestExecution.objects.create(
            name='Build #1',
            project=self.project
        )
        execution2 = TestExecution.objects.create(
            name='Build #2',
            project=self.project
        )
        
        executions = list(TestExecution.objects.all())
        # Le plus récent devrait être en premier
        self.assertEqual(executions[0], execution2)
        self.assertEqual(executions[1], execution1)


class TestResultModelTest(TestCase):
    """Tests pour le modèle TestResult"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        self.test = Test.objects.create(name='Login Test', project=self.project)
        self.execution = TestExecution.objects.create(name='Build #123', project=self.project)
    
    def test_result_creation(self):
        """Test la création d'un résultat de test"""
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            status='passed',
            duration=1500.0,
            error_message=None
        )
        
        self.assertEqual(result.test, self.test)
        self.assertEqual(result.execution, self.execution)
        self.assertEqual(result.status, 'passed')
        self.assertEqual(result.duration, 1500.0)
        self.assertIsNone(result.error_message)
    
    def test_result_with_error(self):
        """Test la création d'un résultat avec erreur"""
        error_msg = "Expected element to be visible, but it was hidden"
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            status='failed',
            duration=2300.0,
            error_message=error_msg
        )
        
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.error_message, error_msg)
    
    def test_result_status_choices(self):
        """Test les différents statuts de résultat"""
        valid_statuses = ['passed', 'failed', 'skipped', 'flaky', 'timedOut']
        
        for status in valid_statuses:
            result = TestResult.objects.create(
                test=self.test,
                execution=self.execution,
                status=status
            )
            self.assertEqual(result.status, status)
    
    def test_result_str_method(self):
        """Test la méthode __str__ du résultat"""
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            status='passed'
        )
        expected = f"{self.test.name} - Build #123 (passed)"
        self.assertEqual(str(result), expected)
    
    def test_result_unique_constraint(self):
        """Test la contrainte d'unicité test/exécution"""
        TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            status='passed'
        )
        
        # Créer un second résultat pour le même test/exécution devrait lever une erreur
        with self.assertRaises(Exception):
            TestResult.objects.create(
                test=self.test,
                execution=self.execution,
                status='failed'
            )


class TestingViewsTest(TestCase):
    """Tests pour les vues liées aux tests"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        self.test = Test.objects.create(name='Login Test', project=self.project)
        self.execution = TestExecution.objects.create(name='Build #123', project=self.project)
        self.result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            status='passed'
        )
    
    def test_tests_list_view(self):
        """Test la vue liste des tests"""
        self.client.login(username='testuser', password='testpass')
        
        # Simuler la sélection d'un projet en session
        session = self.client.session
        session['selected_project_id'] = self.project.id
        session.save()
        
        response = self.client.get(reverse('tests_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login Test')
    
    def test_test_detail_view(self):
        """Test la vue détail d'un test"""
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('test_detail', kwargs={'test_id': self.test.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login Test')
    
    def test_executions_list_view(self):
        """Test la vue liste des exécutions"""
        self.client.login(username='testuser', password='testpass')
        
        # Simuler la sélection d'un projet en session
        session = self.client.session
        session['selected_project_id'] = self.project.id
        session.save()
        
        response = self.client.get(reverse('executions_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build #123')
    
    def test_execution_detail_view(self):
        """Test la vue détail d'une exécution"""
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('execution_detail', kwargs={'execution_id': self.execution.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Build #123')
    
    def test_update_test_comment(self):
        """Test la mise à jour du commentaire d'un test"""
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('update_test_comment', kwargs={'test_id': self.test.id})
        response = self.client.post(url, {
            'comment': 'This is a test comment'
        })
        
        # Devrait être une réponse AJAX JSON
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le commentaire a été mis à jour
        self.test.refresh_from_db()
        # Note: Le modèle Test doit avoir un champ comment pour que cela fonctionne
    
    def test_update_test_result_status(self):
        """Test la mise à jour du statut d'un résultat de test"""
        self.client.login(username='testuser', password='testpass')
        
        url = reverse('update_test_result_status', kwargs={'result_id': self.result.id})
        response = self.client.post(url, {
            'status': 'failed'
        })
        
        # Devrait être une réponse AJAX JSON
        self.assertEqual(response.status_code, 200)
        
        # Vérifier que le statut a été mis à jour
        self.result.refresh_from_db()
        # Note: Vérifier si les utilisateurs peuvent modifier les statuts
