# Views temporaires pour integrations
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Import temporaire - à remplacer par les nouvelles références
def fetch_from_ci(request, project_id):
    from core.views import fetch_from_ci as core_fetch_from_ci
    return core_fetch_from_ci(request, project_id)

def ci_status_check(request, project_id):
    from core.views import ci_status_check as core_ci_status_check
    return core_ci_status_check(request, project_id)
