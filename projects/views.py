# Views temporaires pour projects
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Import temporaire - à remplacer par les nouvelles références
def projects_list(request):
    from core.views import projects_list as core_projects_list
    return core_projects_list(request)

def project_create(request):
    from core.views import project_create as core_project_create
    return core_project_create(request)

def project_detail(request, project_id):
    from core.views import project_detail as core_project_detail
    return core_project_detail(request, project_id)

def project_edit(request, project_id):
    from core.views import project_edit as core_project_edit
    return core_project_edit(request, project_id)

def project_delete(request, project_id):
    from core.views import project_delete as core_project_delete
    return core_project_delete(request, project_id)

def project_features(request, project_id):
    from core.views import project_features as core_project_features
    return core_project_features(request, project_id)

def select_project(request):
    from core.views import select_project as core_select_project
    return core_select_project(request)
