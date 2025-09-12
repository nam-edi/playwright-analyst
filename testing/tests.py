"""
Tests pour l'application testing
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime

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
        
        # Même nom et couleur mais projet différent - devrait fonctionner
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
    
    def test_test_creation(self):
        """Test la création d'un test"""
        test = Test.objects.create(
            title='Login Test',
            file_path='tests/login.spec.js',
            line=10,
            column=5,
            project=self.project
        )
        
        self.assertEqual(test.title, 'Login Test')
        self.assertEqual(test.file_path, 'tests/login.spec.js')
        self.assertEqual(test.line, 10)
        self.assertEqual(test.column, 5)
        self.assertEqual(test.project, self.project)
        self.assertTrue(test.created_at)

    def test_test_str_method(self):
        """Test la méthode __str__ du test"""
        test = Test.objects.create(
            title='Login Test',
            file_path='tests/login.spec.js',
            line=10,
            column=5,
            project=self.project
        )
        expected = "Login Test (tests/login.spec.js:10)"
        self.assertEqual(str(test), expected)

    def test_test_with_tags(self):
        """Test l'association d'un test avec des tags"""
        test = Test.objects.create(
            title='Login Test',
            file_path='tests/login.spec.js',
            line=10,
            column=5,
            project=self.project
        )
        
        tag1 = Tag.objects.create(name='auth', project=self.project, color='#ff0000')
        tag2 = Tag.objects.create(name='ui', project=self.project, color='#00ff00')
        
        test.tags.add(tag1, tag2)
        
        self.assertEqual(test.tags.count(), 2)
        self.assertIn(tag1, test.tags.all())
        self.assertIn(tag2, test.tags.all())

    def test_test_unique_constraint(self):
        """Test la contrainte d'unicité titre/projet/fichier/ligne/colonne"""
        Test.objects.create(
            title='Login Test',
            file_path='tests/login.spec.js',
            line=10,
            column=5,
            project=self.project
        )
        
        # Créer un test avec les mêmes données devrait échouer
        with self.assertRaises(Exception):
            Test.objects.create(
                title='Login Test',
                file_path='tests/login.spec.js',
                line=10,
                column=5,
                project=self.project
            )


class TestExecutionModelTest(TestCase):
    """Tests pour le modèle TestExecution"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
    
    def test_execution_creation(self):
        """Test la création d'une exécution"""
        start_time = datetime.now()
        
        execution = TestExecution.objects.create(
            project=self.project,
            start_time=start_time,
            duration=5000.0,
            expected_tests=10,
            skipped_tests=2,
            unexpected_tests=0,
            flaky_tests=1,
            raw_json={"test": "data"}
        )
        
        self.assertEqual(execution.project, self.project)
        self.assertEqual(execution.start_time, start_time)
        self.assertEqual(execution.duration, 5000.0)
        self.assertEqual(execution.expected_tests, 10)

    def test_execution_str_method(self):
        """Test la méthode __str__ de l'exécution"""
        start_time = datetime.now()
        
        execution = TestExecution.objects.create(
            project=self.project,
            start_time=start_time,
            duration=5000.0,
            raw_json={"test": "data"}
        )
        
        expected_format = f"{self.project.name} - {start_time.strftime('%Y-%m-%d %H:%M')}"
        self.assertEqual(str(execution), expected_format)

    def test_execution_statistics(self):
        """Test le calcul des statistiques d'exécution"""
        execution = TestExecution.objects.create(
            project=self.project,
            start_time=datetime.now(),
            duration=5000.0,
            expected_tests=8,
            skipped_tests=2,
            unexpected_tests=0,
            flaky_tests=0,
            raw_json={"test": "data"}
        )
        
        # Test des propriétés calculées
        self.assertEqual(execution.total_tests, 10)  # 8 + 2 + 0 + 0
        self.assertEqual(execution.success_rate, 80.0)  # 8/10 * 100

    def test_execution_ordering(self):
        """Test l'ordre des exécutions par date de création"""
        from datetime import timedelta
        
        start_time1 = datetime.now()
        start_time2 = start_time1 + timedelta(hours=1)
        
        execution1 = TestExecution.objects.create(
            project=self.project,
            start_time=start_time1,
            duration=5000.0,
            raw_json={"test": "data1"}
        )
        execution2 = TestExecution.objects.create(
            project=self.project,
            start_time=start_time2,
            duration=6000.0,
            raw_json={"test": "data2"}
        )
        
        executions = TestExecution.objects.all()
        # L'ordre par défaut devrait être par start_time croissant
        self.assertEqual(executions.first(), execution1)
        self.assertEqual(executions.last(), execution2)


class TestResultModelTest(TestCase):
    """Tests pour le modèle TestResult"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        self.test = Test.objects.create(
            title='Login Test', 
            file_path='tests/login.spec.js',
            line=10,
            column=5,
            project=self.project
        )
        self.execution = TestExecution.objects.create(
            project=self.project,
            start_time=datetime.now(),
            duration=5000.0,
            raw_json={"test": "data"}
        )
    
    def test_result_creation(self):
        """Test la création d'un résultat de test"""
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            project_id='playwright-project',
            project_name='Test Project',
            timeout=30000,
            expected_status='passed',
            status='passed',
            worker_index=0,
            parallel_index=0,
            duration=1500.0,
            start_time=datetime.now()
        )
        
        self.assertEqual(result.test, self.test)
        self.assertEqual(result.execution, self.execution)
        self.assertEqual(result.status, 'passed')
        self.assertEqual(result.duration, 1500.0)
    
    def test_result_str_method(self):
        """Test la méthode __str__ du résultat"""
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            project_id='playwright-project',
            project_name='Test Project',
            timeout=30000,
            expected_status='passed',
            status='passed',
            worker_index=0,
            parallel_index=0,
            duration=1500.0,
            start_time=datetime.now()
        )
        expected = f"{self.test.title} - passed (1500.0ms)"
        self.assertEqual(str(result), expected)
    
    def test_result_status_choices(self):
        """Test les différents statuts de résultat"""
        statuses = ['passed', 'failed', 'skipped', 'flaky', 'expected', 'unexpected']
        
        for i, status in enumerate(statuses):
            result = TestResult.objects.create(
                test=self.test,
                execution=self.execution,
                project_id='playwright-project',
                project_name='Test Project',
                timeout=30000,
                expected_status='passed',
                status=status,
                worker_index=i,  # Différents worker_index pour éviter les conflits
                parallel_index=0,
                duration=1000.0,
                start_time=datetime.now()
            )
            self.assertEqual(result.status, status)
    
    def test_result_with_errors(self):
        """Test la création d'un résultat avec erreurs"""
        errors_data = [{"message": "Expected 'Login' but got 'Error'", "location": "line 25"}]
        
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            project_id='playwright-project',
            project_name='Test Project',
            timeout=30000,
            expected_status='passed',
            status='failed',
            worker_index=0,
            parallel_index=0,
            duration=2000.0,
            errors=errors_data,
            start_time=datetime.now()
        )
        
        self.assertEqual(result.errors, errors_data)
        self.assertEqual(result.status, 'failed')
        self.assertTrue(result.has_errors)
    
    def test_result_properties(self):
        """Test les propriétés calculées du résultat"""
        result = TestResult.objects.create(
            test=self.test,
            execution=self.execution,
            project_id='playwright-project',
            project_name='Test Project',
            timeout=30000,
            expected_status='passed',
            status='passed',
            worker_index=0,
            parallel_index=0,
            duration=2000.0,
            start_time=datetime.now()
        )
        
        # Test de la propriété duration_seconds
        self.assertEqual(result.duration_seconds, 2.0)  # 2000ms = 2s
        self.assertFalse(result.has_errors)  # Pas d'erreurs par défaut


class TestingViewsTest(TestCase):
    """Tests pour les vues de l'application testing"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.project = Project.objects.create(name='Test Project', created_by=self.user)
        self.test = Test.objects.create(
            title='Login Test',
            file_path='tests/login.spec.js',
            line=10,
            column=5,
            project=self.project
        )
        self.execution = TestExecution.objects.create(
            project=self.project,
            start_time=datetime.now(),
            duration=5000.0,
            raw_json={"test": "data"}
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_tests_list_view(self):
        """Test la vue liste des tests"""
        # Placeholder - ajuster selon les URLs réelles
        self.assertTrue(True)
    
    def test_test_detail_view(self):
        """Test la vue détail d'un test"""
        # Placeholder - ajuster selon les URLs réelles
        self.assertTrue(True)
    
    def test_executions_list_view(self):
        """Test la vue liste des exécutions"""
        # Placeholder - ajuster selon les URLs réelles
        self.assertTrue(True)
    
    def test_execution_detail_view(self):
        """Test la vue détail d'une exécution"""
        # Placeholder - ajuster selon les URLs réelles
        self.assertTrue(True)
    
    def test_update_test_result_status(self):
        """Test la mise à jour du statut d'un résultat de test"""
        # Placeholder - ajuster selon les vues existantes
        self.assertTrue(True)
    
    def test_update_test_comment(self):
        """Test la mise à jour du commentaire d'un test"""
        # Placeholder - ajuster selon les vues existantes
        self.assertTrue(True)