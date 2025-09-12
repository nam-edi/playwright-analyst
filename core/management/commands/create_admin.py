"""
Commande pour créer un utilisateur admin initial
"""

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée un utilisateur admin initial s'il n'existe pas déjà"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="Nom d'utilisateur pour l'admin", default="admin")
        parser.add_argument("--email", type=str, help="Email pour l'admin", default="admin@example.com")
        parser.add_argument("--password", type=str, help="Mot de passe pour l'admin", default="admin123")

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        # Vérifier si l'utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'L\'utilisateur "{username}" existe déjà'))
            return

        # Créer l'utilisateur
        user = User.objects.create_user(username=username, email=email, password=password, is_staff=True, is_superuser=True)

        # Ajouter l'utilisateur au groupe Admin
        try:
            admin_group = Group.objects.get(name="Admin")
            user.groups.add(admin_group)
        except Group.DoesNotExist:
            self.stdout.write(self.style.WARNING("Le groupe Admin n'existe pas. Exécutez d'abord setup_groups."))

        self.stdout.write(
            self.style.SUCCESS(
                f'Utilisateur admin "{username}" créé avec succès !\n'
                f"Email: {email}\n"
                f"Mot de passe: {password}\n"
                f"Connectez-vous à /admin/ ou /accounts/login/"
            )
        )
