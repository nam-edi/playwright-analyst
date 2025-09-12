"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/

Modèles centraux pour l'application core.
Les autres modèles ont été déplacés dans leurs applications respectives :
- Project, ProjectFeature -> projects/models.py
- Tag, TestExecution, Test, TestResult -> testing/models.py
- CIConfiguration, GitLabConfiguration, GitHubConfiguration -> integrations/models.py
- APIKey -> api/models.py
"""

from django.contrib.auth.models import User
from django.db import models


class UserContext(models.Model):
    """
    Association entre un utilisateur et des projets spécifiques.
    Seuls les utilisateurs des groupes Manager et Viewer peuvent avoir un contexte.
    Les Admin accèdent à tout sans restriction.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Utilisateur")
    projects = models.ManyToManyField(
        "projects.Project",
        blank=True,
        verbose_name="Projets accessibles",
        help_text="Si aucun projet n'est sélectionné, l'utilisateur accède à tous les projets",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        verbose_name = "Contexte utilisateur"
        verbose_name_plural = "Contextes utilisateurs"

    def __str__(self):
        projects_count = self.projects.count()
        if projects_count > 0:
            return f"{self.user.username} - {projects_count} projet{'s' if projects_count > 1 else ''}"
        return f"{self.user.username} - Tous les projets"

    def save(self, *args, **kwargs):
        """
        Validation : seuls les utilisateurs Manager et Viewer peuvent avoir un contexte
        """
        user_groups = self.user.groups.values_list("name", flat=True)
        if "Admin" in user_groups:
            raise ValueError("Les utilisateurs Admin ne peuvent pas avoir de contexte")
        super().save(*args, **kwargs)

    def get_projects_count(self):
        """Retourne le nombre de projets dans ce contexte"""
        return self.projects.count()

    @classmethod
    def get_user_accessible_projects(cls, user):
        """
        Retourne les projets accessibles par un utilisateur selon son contexte.
        """
        from projects.models import Project

        # Si l'utilisateur est Admin, il accède à tout
        if user.groups.filter(name="Admin").exists():
            return Project.objects.all()

        # Chercher le contexte de l'utilisateur
        try:
            user_context = cls.objects.get(user=user)
            projects = user_context.projects.all()
            if projects.exists():
                # L'utilisateur a des projets définis, retourner ces projets
                return projects
            else:
                # L'utilisateur n'a pas de projets définis, accès à tous les projets
                return Project.objects.all()
        except cls.DoesNotExist:
            # Pas de contexte défini, accès à tous les projets (comportement actuel)
            return Project.objects.all()


# L'application core ne contient plus de modèles métier,
# seulement des utilitaires et la configuration de base
