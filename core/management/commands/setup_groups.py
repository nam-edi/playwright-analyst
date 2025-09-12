"""
Commande pour créer les groupes et permissions
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from api.models import APIKey
from integrations.models import CIConfiguration
from projects.models import Project, ProjectFeature
from testing.models import Tag, Test, TestExecution, TestResult


class Command(BaseCommand):
    help = "Crée les groupes Admin, Manager et Viewer avec leurs permissions"

    def handle(self, *args, **options):
        # Créer les groupes s'ils n'existent pas
        admin_group, created = Group.objects.get_or_create(name="Admin")
        manager_group, created = Group.objects.get_or_create(name="Manager")
        viewer_group, created = Group.objects.get_or_create(name="Viewer")

        # Récupérer tous les types de contenu de nos modèles
        project_ct = ContentType.objects.get_for_model(Project)
        test_ct = ContentType.objects.get_for_model(Test)
        test_execution_ct = ContentType.objects.get_for_model(TestExecution)
        test_result_ct = ContentType.objects.get_for_model(TestResult)
        tag_ct = ContentType.objects.get_for_model(Tag)
        project_feature_ct = ContentType.objects.get_for_model(ProjectFeature)
        ci_config_ct = ContentType.objects.get_for_model(CIConfiguration)
        api_key_ct = ContentType.objects.get_for_model(APIKey)

        # GROUPE ADMIN - Tous les accès (y compris l'admin Django)
        admin_permissions = Permission.objects.all()
        admin_group.permissions.set(admin_permissions)

        # Permissions spéciales pour l'administration Django
        admin_group.permissions.add(
            Permission.objects.get(codename="add_user"),
            Permission.objects.get(codename="change_user"),
            Permission.objects.get(codename="delete_user"),
            Permission.objects.get(codename="view_user"),
        )

        # GROUPE MANAGER - Accès complet au front, pas d'admin, pas de gestion de projets
        manager_permissions = [
            # Projets - Lecture seule uniquement
            Permission.objects.get(content_type=project_ct, codename="view_project"),
            # Tests - CRUD complet
            Permission.objects.get(content_type=test_ct, codename="add_test"),
            Permission.objects.get(content_type=test_ct, codename="change_test"),
            Permission.objects.get(content_type=test_ct, codename="delete_test"),
            Permission.objects.get(content_type=test_ct, codename="view_test"),
            # Exécutions - CRUD complet
            Permission.objects.get(content_type=test_execution_ct, codename="add_testexecution"),
            Permission.objects.get(content_type=test_execution_ct, codename="change_testexecution"),
            Permission.objects.get(content_type=test_execution_ct, codename="delete_testexecution"),
            Permission.objects.get(content_type=test_execution_ct, codename="view_testexecution"),
            # Résultats de tests - CRUD complet
            Permission.objects.get(content_type=test_result_ct, codename="add_testresult"),
            Permission.objects.get(content_type=test_result_ct, codename="change_testresult"),
            Permission.objects.get(content_type=test_result_ct, codename="delete_testresult"),
            Permission.objects.get(content_type=test_result_ct, codename="view_testresult"),
            # Tags - CRUD complet
            Permission.objects.get(content_type=tag_ct, codename="add_tag"),
            Permission.objects.get(content_type=tag_ct, codename="change_tag"),
            Permission.objects.get(content_type=tag_ct, codename="delete_tag"),
            Permission.objects.get(content_type=tag_ct, codename="view_tag"),
            # Features de projet - CRUD complet
            Permission.objects.get(content_type=project_feature_ct, codename="add_projectfeature"),
            Permission.objects.get(content_type=project_feature_ct, codename="change_projectfeature"),
            Permission.objects.get(content_type=project_feature_ct, codename="delete_projectfeature"),
            Permission.objects.get(content_type=project_feature_ct, codename="view_projectfeature"),
            # Configuration CI - CRUD complet
            Permission.objects.get(content_type=ci_config_ct, codename="add_ciconfiguration"),
            Permission.objects.get(content_type=ci_config_ct, codename="change_ciconfiguration"),
            Permission.objects.get(content_type=ci_config_ct, codename="delete_ciconfiguration"),
            Permission.objects.get(content_type=ci_config_ct, codename="view_ciconfiguration"),
            # Clés API - CRUD complet
            Permission.objects.get(content_type=api_key_ct, codename="add_apikey"),
            Permission.objects.get(content_type=api_key_ct, codename="change_apikey"),
            Permission.objects.get(content_type=api_key_ct, codename="delete_apikey"),
            Permission.objects.get(content_type=api_key_ct, codename="view_apikey"),
        ]

        manager_group.permissions.set(manager_permissions)

        # GROUPE VIEWER - Lecture seule uniquement
        viewer_permissions = [
            # Projets - Lecture seule
            Permission.objects.get(content_type=project_ct, codename="view_project"),
            # Tests - Lecture seule
            Permission.objects.get(content_type=test_ct, codename="view_test"),
            # Exécutions - Lecture seule
            Permission.objects.get(content_type=test_execution_ct, codename="view_testexecution"),
            # Résultats de tests - Lecture seule
            Permission.objects.get(content_type=test_result_ct, codename="view_testresult"),
            # Tags - Lecture seule
            Permission.objects.get(content_type=tag_ct, codename="view_tag"),
            # Features de projet - Lecture seule
            Permission.objects.get(content_type=project_feature_ct, codename="view_projectfeature"),
            # Configuration CI - Lecture seule
            Permission.objects.get(content_type=ci_config_ct, codename="view_ciconfiguration"),
            # Clés API - Lecture seule
            Permission.objects.get(content_type=api_key_ct, codename="view_apikey"),
        ]

        viewer_group.permissions.set(viewer_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f"Groupes créés avec succès:\n"
                f"- Admin: {admin_group.permissions.count()} permissions\n"
                f"- Manager: {manager_group.permissions.count()} permissions\n"
                f"- Viewer: {viewer_group.permissions.count()} permissions"
            )
        )
