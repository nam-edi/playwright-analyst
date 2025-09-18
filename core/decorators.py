"""
Décorateurs pour vérifier la configuration initiale
"""

from functools import wraps

from django.contrib.auth.models import Group
from django.shortcuts import redirect

from projects.models import Project


def setup_required(view_func):
    """
    Décorateur qui vérifie si la configuration initiale est terminée.
    Redirige vers la page de setup si ce n'est pas le cas.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Si l'utilisateur n'est pas authentifié, laisser la vue gérer cela
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        # Vérifier si la configuration initiale est terminée
        groups_exist = Group.objects.filter(name__in=["Admin", "Manager", "Viewer"]).count() == 3

        superuser_in_admin = False
        if request.user.is_superuser and groups_exist:
            superuser_in_admin = request.user.groups.filter(name="Admin").exists()

        project_exists = Project.objects.exists()

        # Si la configuration n'est pas terminée, rediriger vers la page de setup
        if not (groups_exist and superuser_in_admin and project_exists):
            return redirect("setup_actions")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def is_setup_complete(user):
    """
    Fonction utilitaire pour vérifier si la configuration initiale est terminée
    """
    if not user.is_authenticated:
        return False

    # Vérifier si les groupes sont créés
    groups_exist = Group.objects.filter(name__in=["Admin", "Manager", "Viewer"]).count() == 3

    # Vérifier si le superuser est dans le groupe Admin
    superuser_in_admin = False
    if user.is_superuser and groups_exist:
        superuser_in_admin = user.groups.filter(name="Admin").exists()

    # Vérifier si au moins un projet existe
    project_exists = Project.objects.exists()

    return groups_exist and superuser_in_admin and project_exists
