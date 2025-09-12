"""
Commande pour créer des utilisateurs de démonstration
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée des utilisateurs de démonstration pour tester les permissions"

    def handle(self, *args, **options):
        # Récupérer les groupes
        try:
            admin_group = Group.objects.get(name="Admin")
            manager_group = Group.objects.get(name="Manager")
            viewer_group = Group.objects.get(name="Viewer")
        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR("Les groupes n'existent pas. Exécutez d'abord setup_groups."))
            return

        # Créer un utilisateur Manager
        if not User.objects.filter(username="manager").exists():
            manager_user = User.objects.create_user(
                username="manager",
                email="manager@example.com",
                password="manager123",
                first_name="John",
                last_name="Manager",
                is_staff=False,
                is_superuser=False,
            )
            manager_user.groups.add(manager_group)
            self.stdout.write(self.style.SUCCESS('Utilisateur "manager" créé (mot de passe: manager123)'))

        # Créer un utilisateur Viewer
        if not User.objects.filter(username="viewer").exists():
            viewer_user = User.objects.create_user(
                username="viewer",
                email="viewer@example.com",
                password="viewer123",
                first_name="Jane",
                last_name="Viewer",
                is_staff=False,
                is_superuser=False,
            )
            viewer_user.groups.add(viewer_group)
            self.stdout.write(self.style.SUCCESS('Utilisateur "viewer" créé (mot de passe: viewer123)'))

        # Créer un utilisateur Admin (si pas déjà existant)
        if not User.objects.filter(username="superadmin").exists():
            admin_user = User.objects.create_user(
                username="superadmin",
                email="superadmin@example.com",
                password="admin123",
                first_name="Super",
                last_name="Admin",
                is_staff=True,
                is_superuser=True,
            )
            admin_user.groups.add(admin_group)
            self.stdout.write(self.style.SUCCESS('Utilisateur "superadmin" créé (mot de passe: admin123)'))

        self.stdout.write(
            self.style.SUCCESS(
                "\nUtilisateurs de démonstration créés !\n\n"
                "🔴 Admin: superadmin / admin123 (Accès complet)\n"
                "🟡 Manager: manager / manager123 (Peut tout modifier sauf admin)\n"
                "🟢 Viewer: viewer / viewer123 (Lecture seule)\n\n"
                "Testez les différents niveaux d'accès sur /accounts/login/"
            )
        )
