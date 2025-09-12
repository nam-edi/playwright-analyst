"""
URLs pour l'application testing
"""

from django.urls import path

from . import views

app_name = "testing"

urlpatterns = [
    path("tests/", views.tests_list, name="tests_list"),
    path("executions/", views.executions_list, name="executions_list"),
    path("execution/<int:execution_id>/", views.execution_detail, name="execution_detail"),
    path("test/<int:test_id>/", views.test_detail, name="test_detail"),
    path("test/<int:test_id>/comment/", views.update_test_comment, name="update_test_comment"),
    path("execution/<int:execution_id>/comment/", views.update_execution_comment, name="update_execution_comment"),
    path("result/<int:result_id>/status/", views.update_test_result_status, name="update_test_result_status"),
    path("upload/", views.upload_json, name="upload_json"),
    path("upload/process/", views.process_json_upload, name="process_json_upload"),
]
