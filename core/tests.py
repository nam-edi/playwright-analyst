"""
Tests pour l'application core
"""

from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import UserContext
from core.permissions import admin_required, group_required, manager_required
from core.services.context_service import ContextService
from projects.models import Project


class UserContextModelTest(TestCase):
    """Tests pour le modèle UserContext"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass", is_superuser=True)
        self.project1 = Project.objects.create(name="Test Project 1", created_by=self.user)
        self.project2 = Project.objects.create(name="Test Project 2", created_by=self.user)

        # Créer les groupes
        self.admin_group = Group.objects.create(name="Admin")
        self.manager_group = Group.objects.create(name="Manager")
        self.viewer_group = Group.objects.create(name="Viewer")

    def test_user_context_creation(self):
        """Test la création d'un UserContext"""
        context = UserContext.objects.create(user=self.user)
        self.assertEqual(str(context), f"{self.user.username} - Tous les projets")

        # Ajouter des projets
        context.projects.add(self.project1)
        context.refresh_from_db()
        self.assertEqual(str(context), f"{self.user.username} - 1 projet")

        context.projects.add(self.project2)
        context.refresh_from_db()
        self.assertEqual(str(context), f"{self.user.username} - 2 projets")

    def test_user_context_unique_constraint(self):
        """Test que chaque utilisateur ne peut avoir qu'un seul contexte"""
        UserContext.objects.create(user=self.user)

        # Essayer de créer un second contexte devrait lever une erreur
        with self.assertRaises(Exception):
            UserContext.objects.create(user=self.user)


class ContextServiceTest(TestCase):
    """Tests pour ContextService"""

    def setUp(self):
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        self.manager_user = User.objects.create_user(username="manager", password="managerpass")
        self.viewer_user = User.objects.create_user(username="viewer", password="viewerpass")

        # Créer les groupes
        self.admin_group = Group.objects.create(name="Admin")
        self.manager_group = Group.objects.create(name="Manager")
        self.viewer_group = Group.objects.create(name="Viewer")

        # Assigner les utilisateurs aux groupes
        self.admin_user.groups.add(self.admin_group)
        self.manager_user.groups.add(self.manager_group)
        self.viewer_user.groups.add(self.viewer_group)

        # Créer des projets
        self.project1 = Project.objects.create(name="Project 1", created_by=self.admin_user)
        self.project2 = Project.objects.create(name="Project 2", created_by=self.admin_user)

        # Créer un contexte pour le viewer avec accès limité
        self.viewer_context = UserContext.objects.create(user=self.viewer_user)
        self.viewer_context.projects.add(self.project1)

    def test_admin_access_all_projects(self):
        """Test qu'un admin accède à tous les projets"""
        accessible_projects = ContextService.get_user_accessible_projects(self.admin_user)
        self.assertEqual(accessible_projects.count(), 2)

    def test_viewer_access_restricted_projects(self):
        """Test qu'un viewer n'accède qu'aux projets de son contexte"""
        accessible_projects = ContextService.get_user_accessible_projects(self.viewer_user)
        self.assertEqual(accessible_projects.count(), 1)
        self.assertEqual(accessible_projects.first(), self.project1)

    def test_can_user_access_project(self):
        """Test la vérification d'accès à un projet spécifique"""
        # Admin peut accéder à tout
        self.assertTrue(ContextService.can_user_access_project(self.admin_user, self.project1))
        self.assertTrue(ContextService.can_user_access_project(self.admin_user, self.project2))

        # Viewer ne peut accéder qu'au projet 1
        self.assertTrue(ContextService.can_user_access_project(self.viewer_user, self.project1))
        self.assertFalse(ContextService.can_user_access_project(self.viewer_user, self.project2))


class PermissionsTest(TestCase):
    """Tests pour les décorateurs de permissions"""

    def setUp(self):
        self.client = Client()

        # Créer les groupes
        self.admin_group = Group.objects.create(name="Admin")
        self.manager_group = Group.objects.create(name="Manager")
        self.viewer_group = Group.objects.create(name="Viewer")

        # Créer les utilisateurs
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")
        self.manager_user = User.objects.create_user(username="manager", password="managerpass")
        self.viewer_user = User.objects.create_user(username="viewer", password="viewerpass")
        self.no_group_user = User.objects.create_user(username="nogroup", password="nogrouppass")

        # Assigner aux groupes
        self.admin_user.groups.add(self.admin_group)
        self.manager_user.groups.add(self.manager_group)
        self.viewer_user.groups.add(self.viewer_group)

    def test_admin_required_decorator(self):
        """Test que les utilisateurs connectés peuvent accéder au dashboard admin"""
        # Test avec admin
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Test avec manager (peut aussi accéder car seul @login_required)
        self.client.login(username="manager", password="managerpass")
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 200)  # Accès autorisé

    def test_manager_required_decorator(self):
        """Test que seuls les admins peuvent gérer les projets"""
        # Test avec admin (devrait marcher)
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(reverse("project_create"))
        self.assertEqual(response.status_code, 200)

        # Test avec manager (devrait être redirigé car @can_manage_projects = Admin seulement)
        self.client.login(username="manager", password="managerpass")
        response = self.client.get(reverse("project_create"))
        self.assertEqual(response.status_code, 302)  # Redirection

        # Test avec viewer (devrait être redirigé)
        self.client.login(username="viewer", password="viewerpass")
        response = self.client.get(reverse("project_create"))
        self.assertEqual(response.status_code, 302)  # Redirection


class CoreViewsTest(TestCase):
    """Tests pour les vues de l'application core"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.admin_user = User.objects.create_user(username="admin", password="adminpass")

        # Créer les groupes
        self.admin_group = Group.objects.create(name="Admin")
        self.admin_user.groups.add(self.admin_group)

        self.project = Project.objects.create(name="Test Project", created_by=self.user)

    def test_home_view_redirect_anonymous(self):
        """Test que la vue home redirige les utilisateurs anonymes"""
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)  # Redirection vers login

    def test_home_view_authenticated(self):
        """Test que la vue home fonctionne pour les utilisateurs connectés"""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_select_project_view(self):
        """Test la sélection de projet"""
        self.client.login(username="testuser", password="testpass")

        # Test GET - redirige vers home
        response = self.client.get(reverse("select_project"))
        self.assertEqual(response.status_code, 302)  # Redirection vers home

        # Test POST - sélectionne un projet (nécessite UserContext configuré)
        # Créer un contexte utilisateur pour que le projet soit accessible
        from core.models import UserContext

        user_context = UserContext.objects.create(user=self.user)
        user_context.projects.add(self.project)

        response = self.client.post(reverse("select_project"), {"project_id": self.project.id})
        # La vue retourne une réponse HTMX avec header HX-Redirect
        self.assertEqual(response.status_code, 200)

    def test_administration_dashboard_access(self):
        """Test l'accès au tableau de bord d'administration"""
        # Utilisateur connecté peut accéder (seul @login_required)
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 200)  # Accès autorisé

        # Admin devrait pouvoir accéder aussi
        self.client.login(username="admin", password="adminpass")
        response = self.client.get(reverse("administration_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_documentation_view(self):
        """Test la vue de documentation"""
        self.client.login(username="testuser", password="testpass")
        response = self.client.get(reverse("documentation"))
        self.assertEqual(response.status_code, 200)
