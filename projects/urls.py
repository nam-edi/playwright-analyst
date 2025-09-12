"""
URLs pour l'application projects
"""

from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.projects_list, name="list"),
    path("create/", views.project_create, name="create"),
    path("<int:project_id>/", views.project_detail, name="detail"),
    path("<int:project_id>/edit/", views.project_edit, name="edit"),
    path("<int:project_id>/delete/", views.project_delete, name="delete"),
    path("<int:project_id>/features/", views.project_features, name="features"),
    path("select/", views.select_project, name="select"),
]
