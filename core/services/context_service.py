"""
Service pour la gestion des contextes utilisateurs
"""

from django.contrib.auth.models import User
from django.db.models import Q
from projects.models import Project
from core.models import UserContext


class ContextService:
    """Service pour gérer les contextes d'accès des utilisateurs"""

    @staticmethod
    def get_user_accessible_projects(user):
        """
        Retourne les projets accessibles par un utilisateur selon son contexte.
        
        Args:
            user (User): L'utilisateur pour lequel récupérer les projets
            
        Returns:
            QuerySet: Les projets accessibles
        """
        return UserContext.get_user_accessible_projects(user)

    @staticmethod
    def can_user_access_project(user, project):
        """
        Vérifie si un utilisateur peut accéder à un projet spécifique.
        
        Args:
            user (User): L'utilisateur
            project (Project): Le projet à vérifier
            
        Returns:
            bool: True si l'utilisateur peut accéder au projet
        """
        accessible_projects = ContextService.get_user_accessible_projects(user)
        return accessible_projects.filter(id=project.id).exists()

    @staticmethod
    def get_user_context(user):
        """
        Récupère le contexte d'un utilisateur.
        
        Args:
            user (User): L'utilisateur
            
        Returns:
            UserContext or None: Le contexte de l'utilisateur ou None
        """
        try:
            return UserContext.objects.prefetch_related('projects').get(user=user)
        except UserContext.DoesNotExist:
            return None

    @staticmethod
    def set_user_projects(user, projects):
        """
        Définit les projets accessibles pour un utilisateur.
        
        Args:
            user (User): L'utilisateur
            projects (list): Liste des projets à assigner
            
        Returns:
            UserContext: Le contexte utilisateur créé ou mis à jour
        """
        # Vérifier que l'utilisateur n'est pas Admin
        if user.groups.filter(name='Admin').exists():
            raise ValueError("Les utilisateurs Admin ne peuvent pas avoir de contexte")
            
        user_context, created = UserContext.objects.get_or_create(user=user)
        user_context.projects.set(projects)
        return user_context

    @staticmethod
    def add_project_to_user(user, project):
        """
        Ajoute un projet au contexte d'un utilisateur.
        
        Args:
            user (User): L'utilisateur
            project (Project): Le projet à ajouter
        """
        user_context, created = UserContext.objects.get_or_create(user=user)
        user_context.projects.add(project)

    @staticmethod
    def remove_project_from_user(user, project):
        """
        Retire un projet du contexte d'un utilisateur.
        
        Args:
            user (User): L'utilisateur
            project (Project): Le projet à retirer
        """
        try:
            user_context = UserContext.objects.get(user=user)
            user_context.projects.remove(project)
        except UserContext.DoesNotExist:
            pass

    @staticmethod
    def remove_user_context(user):
        """
        Supprime le contexte d'un utilisateur.
        
        Args:
            user (User): L'utilisateur
        """
        try:
            user_context = UserContext.objects.get(user=user)
            user_context.delete()
        except UserContext.DoesNotExist:
            pass

    @staticmethod
    def get_users_with_restricted_access():
        """
        Récupère tous les utilisateurs ayant un accès restreint (avec des projets spécifiques).
        
        Returns:
            QuerySet: Les utilisateurs ayant un contexte avec des projets spécifiques
        """
        return User.objects.filter(
            usercontext__isnull=False,
            usercontext__projects__isnull=False
        ).distinct()

    @staticmethod
    def get_users_without_context():
        """
        Récupère tous les utilisateurs Manager/Viewer sans contexte défini ou avec accès à tous les projets.
        
        Returns:
            QuerySet: Les utilisateurs sans contexte
        """
        # Utilisateurs Manager/Viewer qui n'ont pas de UserContext
        # ou qui ont un UserContext sans projets spécifiques
        manager_viewer_users = User.objects.filter(
            groups__name__in=['Manager', 'Viewer']
        ).distinct()
        
        # Exclure ceux qui ont un UserContext avec des projets spécifiques
        users_with_restricted_access = ContextService.get_users_with_restricted_access()
        
        return manager_viewer_users.exclude(id__in=users_with_restricted_access.values_list('id', flat=True))

    @staticmethod
    def filter_projects_by_context(projects_queryset, user):
        """
        Filtre un queryset de projets selon le contexte de l'utilisateur.
        
        Args:
            projects_queryset (QuerySet): Le queryset de projets à filtrer
            user (User): L'utilisateur
            
        Returns:
            QuerySet: Le queryset filtré
        """
        accessible_projects = ContextService.get_user_accessible_projects(user)
        return projects_queryset.filter(id__in=accessible_projects.values_list('id', flat=True))

    @staticmethod
    def get_context_statistics():
        """
        Récupère des statistiques sur les contextes.
        
        Returns:
            dict: Statistiques des contextes
        """
        total_user_contexts = UserContext.objects.count()
        users_with_restricted_access = ContextService.get_users_with_restricted_access().count()
        users_without_context = ContextService.get_users_without_context().count()
        
        return {
            'total_user_contexts': total_user_contexts,
            'users_with_restricted_access': users_with_restricted_access,
            'users_without_context': users_without_context,
        }