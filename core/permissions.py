"""
Decorators personnalisés pour gérer les permissions par groupe
"""

from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect


def group_required(*group_names):
    """
    Décorateur qui vérifie si l'utilisateur fait partie d'un des groupes spécifiés.
    Usage: @group_required('Admin', 'Manager')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            user_groups = request.user.groups.values_list('name', flat=True)
            
            if any(group in user_groups for group in group_names):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, 'Vous n\'avez pas les permissions nécessaires pour accéder à cette page.')
                return redirect('home')
        
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """
    Décorateur pour les vues qui nécessitent les permissions d'administrateur.
    """
    return group_required('Admin')(view_func)


def manager_required(view_func):
    """
    Décorateur pour les vues qui nécessitent les permissions de manager ou plus.
    """
    return group_required('Admin', 'Manager')(view_func)


def can_modify_data(view_func):
    """
    Décorateur pour les vues qui nécessitent la permission de modifier des données.
    Les Viewers ne peuvent pas modifier de données.
    """
    return group_required('Admin', 'Manager')(view_func)


def can_manage_projects(view_func):
    """
    Décorateur pour les vues qui nécessitent la permission de gérer les projets.
    Seuls les Admins peuvent créer, modifier et supprimer des projets.
    """
    return group_required('Admin')(view_func)


def can_manage_tags(view_func):
    """
    Décorateur pour les vues qui nécessitent la permission de gérer les tags.
    Les Admins et Managers peuvent gérer les tags (couleurs, etc.).
    """
    return group_required('Admin', 'Manager')(view_func)


def can_view_admin(user):
    """
    Fonction de test pour vérifier si l'utilisateur peut accéder à l'admin Django.
    """
    return user.is_superuser or user.groups.filter(name='Admin').exists()


def admin_access_required(view_func):
    """
    Décorateur pour l'accès à l'administration Django.
    """
    return user_passes_test(can_view_admin, login_url='/accounts/login/')(view_func)


def is_viewer_only(user):
    """
    Vérifie si l'utilisateur est uniquement dans le groupe Viewer.
    """
    if user.is_superuser:
        return False
    
    user_groups = user.groups.values_list('name', flat=True)
    return 'Viewer' in user_groups and 'Admin' not in user_groups and 'Manager' not in user_groups


def get_user_permissions(user):
    """
    Retourne un dictionnaire avec les permissions de l'utilisateur.
    """
    if user.is_superuser:
        return {
            'is_admin': True,
            'is_manager': True,
            'is_viewer': True,
            'can_access_admin': True,
            'can_modify': True,
            'can_delete': True,
            'can_create': True,
            'can_manage_projects': True,  # Superutilisateurs peuvent gérer les projets
            'can_manage_tags': True,  # Superutilisateurs peuvent gérer les tags
        }
    
    user_groups = user.groups.values_list('name', flat=True)
    
    is_admin = 'Admin' in user_groups
    is_manager = 'Manager' in user_groups
    is_viewer = 'Viewer' in user_groups
    
    return {
        'is_admin': is_admin,
        'is_manager': is_manager,
        'is_viewer': is_viewer,
        'can_access_admin': is_admin,
        'can_modify': is_admin or is_manager,
        'can_delete': is_admin or is_manager,
        'can_create': is_admin or is_manager,
        'can_manage_projects': is_admin,  # Seuls les admins peuvent gérer les projets
        'can_manage_tags': is_admin or is_manager,  # Admins et managers peuvent gérer les tags
    }