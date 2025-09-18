"""
Middleware pour gérer la redirection vers la page de setup
"""

from django.contrib.auth.models import Group
from django.shortcuts import redirect

from projects.models import Project


class SetupMiddleware:
    """
    Middleware qui redirige vers la page de setup si la configuration initiale n'est pas terminée
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URLs qui ne nécessitent pas la configuration initiale
        self.exempt_urls = [
            "login",
            "logout",
            "setup_actions",
            "create_groups_and_assign_admin",
            "project_create",
            "setup_status",
        ]

        # Chemins d'URLs qui ne nécessitent pas la configuration initiale
        self.exempt_paths = ["/admin/", "/setup/", "/accounts/", "/static/", "/media/", "/documentation/", "/project/create/"]

    def __call__(self, request):
        # Si l'utilisateur n'est pas authentifié, ne pas appliquer le middleware
        if not request.user.is_authenticated:
            response = self.get_response(request)
            return response

        # Si on est sur une URL exemptée, ne pas appliquer le middleware
        if self._is_exempt_url(request):
            response = self.get_response(request)
            return response

        # Vérifier si la configuration initiale est terminée
        if not self._is_setup_complete(request.user):
            # Éviter la boucle de redirection si on est déjà sur la page setup
            if not request.path.startswith("/setup/"):
                return redirect("setup_actions")

        response = self.get_response(request)
        return response

    def _is_exempt_url(self, request):
        """Vérifier si l'URL actuelle est exemptée"""
        current_path = request.path
        current_url = request.resolver_match.url_name if request.resolver_match else None

        # Vérifier les chemins exemptés en premier
        for exempt_path in self.exempt_paths:
            if current_path.startswith(exempt_path):
                return True

        # Vérifier les noms d'URLs exemptés
        if current_url and current_url in self.exempt_urls:
            return True

        return False

    def _is_setup_complete(self, user):
        """Vérifier si la configuration initiale est terminée"""
        # Vérifier si les groupes sont créés
        groups_exist = Group.objects.filter(name__in=["Admin", "Manager", "Viewer"]).count() == 3

        # Vérifier si le superuser est dans le groupe Admin
        superuser_in_admin = False
        if user.is_superuser and groups_exist:
            superuser_in_admin = user.groups.filter(name="Admin").exists()

        # Vérifier si au moins un projet existe
        project_exists = Project.objects.exists()

        return groups_exist and superuser_in_admin and project_exists
