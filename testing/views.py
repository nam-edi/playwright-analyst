# Views temporaires pour testing
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Import temporaire - à remplacer par les nouvelles références
def tests_list(request):
    from core.views import tests_list as core_tests_list
    return core_tests_list(request)

def executions_list(request):
    from core.views import executions_list as core_executions_list
    return core_executions_list(request)

def execution_detail(request, execution_id):
    from core.views import execution_detail as core_execution_detail
    return core_execution_detail(request, execution_id)

def test_detail(request, test_id):
    from core.views import test_detail as core_test_detail
    return core_test_detail(request, test_id)

def update_test_comment(request, test_id):
    from core.views import update_test_comment as core_update_test_comment
    return core_update_test_comment(request, test_id)

def update_execution_comment(request, execution_id):
    from core.views import update_execution_comment as core_update_execution_comment
    return core_update_execution_comment(request, execution_id)

def update_test_result_status(request, result_id):
    from core.views import update_test_result_status as core_update_test_result_status
    return core_update_test_result_status(request, result_id)

def upload_json(request):
    from core.views import upload_json as core_upload_json
    return core_upload_json(request)

def process_json_upload(request):
    from core.views import process_json_upload as core_process_json_upload
    return core_process_json_upload(request)
