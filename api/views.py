# Views temporaires pour api
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Import temporaire - à remplacer par les nouvelles références
def api_upload_results(request, project_id):
    from core.views import api_upload_results as core_api_upload_results
    return core_api_upload_results(request, project_id)

def api_documentation(request):
    from core.views import api_documentation as core_api_documentation
    return core_api_documentation(request)

def api_key_help(request):
    from core.views import api_key_help as core_api_key_help
    return core_api_key_help(request)
