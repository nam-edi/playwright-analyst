from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('tests/', views.tests_list, name='tests_list'),
    path('executions/', views.executions_list, name='executions_list'),
    path('execution/<int:execution_id>/', views.execution_detail, name='execution_detail'),
    path('test/<int:test_id>/', views.test_detail, name='test_detail'),
    path('test/<int:test_id>/comment/', views.update_test_comment, name='update_test_comment'),
    path('select-project/', views.select_project, name='select_project'),
    path('upload/', views.upload_json, name='upload_json'),
    path('upload/process/', views.process_json_upload, name='process_json_upload'),
    path('fetch-ci/<int:project_id>/', views.fetch_from_ci, name='fetch_from_ci'),
    path('ci-status/<int:project_id>/', views.ci_status_check, name='ci_status_check'),
    path('htmx-example/', views.htmx_example, name='htmx_example'),
]