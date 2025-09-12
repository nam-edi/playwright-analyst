from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    path('', views.home, name='home'),
    path('administration/', views.administration_dashboard, name='administration_dashboard'),
    path('documentation/', views.documentation, name='documentation'),
    path('admin-redirect/', views.admin_redirect, name='admin_redirect'),
    
    # Tests views (temporarily in core during migration)
    path('tests/', views.tests_list, name='tests_list'),
    path('test/<int:test_id>/', views.test_detail, name='test_detail'),
    path('test/<int:test_id>/update-comment/', views.update_test_comment, name='update_test_comment'),
    path('test-result/<int:result_id>/update-status/', views.update_test_result_status, name='update_test_result_status'),
    
    # Execution views (temporarily in core during migration)
    path('executions/', views.executions_list, name='executions_list'),
    path('execution/<int:execution_id>/', views.execution_detail, name='execution_detail'),
    path('execution/<int:execution_id>/update-comment/', views.update_execution_comment, name='update_execution_comment'),
    
    # Project management
    path('select-project/', views.select_project, name='select_project'),
    path('project/create/', views.project_create, name='project_create'),
    path('project/<int:project_id>/edit/', views.project_edit, name='project_edit'),
    path('project/<int:project_id>/delete/', views.project_delete, name='project_delete'),
    path('project/<int:project_id>/features/', views.project_features, name='project_features'),
    path('project/<int:project_id>/ci-status/', views.ci_status_check, name='ci_status_check'),
    
    # Import views
    path('upload/', views.upload_json, name='upload_json'),
    path('upload/process/', views.process_json_upload, name='process_json_upload'),
    path('project/<int:project_id>/fetch-ci/', views.fetch_from_ci, name='fetch_from_ci'),
    
    # API views
    path('project/<int:project_id>/api/upload/', views.api_upload_results, name='api_upload_results'),
    path('api/docs/', views.api_documentation, name='api_documentation'),
    path('help/api-keys/', views.api_key_help, name='api_key_help'),
    
    # User management (Admin only)
    path('admin/users/', admin_views.users_list, name='users_list'),
    path('admin/users/<int:user_id>/edit/', admin_views.user_edit, name='user_edit'),
    path('admin/users/<int:user_id>/toggle-active/', admin_views.user_toggle_active, name='user_toggle_active'),
    path('admin/groups/', admin_views.groups_info, name='groups_info'),
    path('admin/groups/list/', admin_views.groups_list, name='groups_list'),
    path('help/groups/', views.help_groups_permissions, name='help_groups_permissions'),
    
    # Context management (Admin only)
    path('admin/contexts/', admin_views.contexts_info, name='contexts_info'),
    path('admin/user-contexts/', admin_views.user_contexts_list, name='user_contexts_list'),
    
    # URLs pour la gestion des tags
    path('tags/update-color/', admin_views.update_tag_color, name='update_tag_color'),
]