"""
Context processors pour rendre les permissions disponibles dans tous les templates
"""

from .permissions import get_user_permissions
from .services.context_service import ContextService


def user_permissions(request):
    """
    Ajoute les permissions de l'utilisateur au contexte de tous les templates.
    """
    if request.user.is_authenticated:
        permissions = get_user_permissions(request.user)
    else:
        permissions = {
            'is_admin': False,
            'is_manager': False,
            'is_viewer': False,
            'can_access_admin': False,
            'can_modify': False,
            'can_delete': False,
            'can_create': False,
        }
    
    return {'user_permissions': permissions}


def project_context(request):
    """
    Ajoute les informations de projet au contexte de tous les templates.
    """
    if request.user.is_authenticated:
        # Récupérer tous les projets accessibles à l'utilisateur
        projects = ContextService.get_user_accessible_projects(request.user)
        projects_count = projects.count()
        
        # Déterminer le projet sélectionné
        selected_project = None
        project_id = request.session.get('selected_project_id')
        
        # Si un seul projet est accessible, le sélectionner automatiquement
        if projects_count == 1:
            selected_project = projects.first()
            request.session['selected_project_id'] = selected_project.id
        elif project_id:
            try:
                selected_project = projects.get(id=project_id)
            except:
                # Nettoyer la session si le projet n'existe pas ou n'est pas accessible
                if 'selected_project_id' in request.session:
                    del request.session['selected_project_id']
        
        return {
            'projects': projects,
            'selected_project': selected_project,
            'show_project_selector': projects_count > 1,
        }
    
    return {
        'projects': [],
        'selected_project': None,
        'show_project_selector': False,
    }