"""
URLs pour l'application integrations
"""

from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    path('fetch-ci/<int:project_id>/', views.fetch_from_ci, name='fetch_from_ci'),
    path('ci-status/<int:project_id>/', views.ci_status_check, name='ci_status_check'),
]