"""
URLs pour l'application API
"""

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('projects/<int:project_id>/upload/', views.api_upload_results, name='upload_results'),
    path('documentation/', views.api_documentation, name='documentation'),
    path('keys/help/', views.api_key_help, name='key_help'),
]