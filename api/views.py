# Views temporaires pour api

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from core.services.context_service import ContextService
from testing.models import TestExecution


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


@login_required
def get_flaky_tests(request, execution_id):
    """
    API endpoint pour récupérer les tests instables d'une exécution spécifique
    """
    try:
        execution = TestExecution.objects.get(id=execution_id)

        # Vérifier que l'utilisateur peut accéder au projet de cette exécution
        accessible_projects = ContextService.get_user_accessible_projects(request.user)
        if not accessible_projects.filter(id=execution.project.id).exists():
            return JsonResponse({"error": "Accès refusé"}, status=403)

        # Récupérer les tests instables (flaky) de cette exécution avec détails
        results = execution.test_results.exclude(expected_status="skipped")
        flaky_results = results.filter(retry__gt=0, status="passed").select_related("test")

        flaky_tests = []
        for result in flaky_results:
            flaky_tests.append(
                {
                    "title": result.test.title,
                    "retry_count": result.retry,
                    "duration": result.duration,
                    "file_path": result.test.file_path,
                    "test_id": result.test.test_id,
                    "line": result.test.line,
                    "column": result.test.column,
                }
            )

        # Trier par nombre de retries décroissant
        flaky_tests.sort(key=lambda x: x["retry_count"], reverse=True)

        return JsonResponse({"flaky_tests": flaky_tests, "execution_id": execution_id, "count": len(flaky_tests)})

    except TestExecution.DoesNotExist:
        return JsonResponse({"error": "Exécution introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
