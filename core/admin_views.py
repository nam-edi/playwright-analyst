"""
Vues personnalisées pour l'interface d'administration
"""

from django.contrib import admin, messages
from django.contrib.auth.models import Group, User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from projects.models import Project
from testing.models import TestExecution

from .permissions import admin_required, can_manage_tags


def admin_index_view(request, extra_context=None):
    """Vue personnalisée pour la page d'accueil admin avec métriques"""
    extra_context = extra_context or {}

    # Métriques principales
    projects_count = Project.objects.count()
    executions_count = TestExecution.objects.count()
    users_count = User.objects.count()

    # Données pour le graphique d'évolution du taux de réussite par projet
    projects_data = []
    projects = Project.objects.filter(executions__isnull=False).distinct()[:5]  # Limiter à 5 projets pour la lisibilité

    for project in projects:
        recent_executions = project.executions.order_by("-start_time")[:10]  # 10 dernières exécutions par projet
        success_rates = []

        for execution in recent_executions:
            total_tests = execution.test_results.exclude(expected_status="skipped").count()
            passed_tests = execution.test_results.filter(status="passed").count()
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            success_rates.append(round(success_rate, 1))

        # Inverser pour avoir les plus récentes à droite
        success_rates.reverse()

        if success_rates:  # Seulement ajouter si il y a des données
            projects_data.append({"name": project.name, "data": success_rates, "color": generate_project_color(project.id)})

    # Ajouter les données au contexte
    extra_context.update(
        {
            "projects_count": projects_count,
            "executions_count": executions_count,
            "users_count": users_count,
            "projects_data": projects_data,
        }
    )

    # Utiliser la méthode originale sauvegardée pour éviter la récursion
    return original_index(request, extra_context)


def generate_project_color(project_id):
    """Génère une couleur unique pour chaque projet basée sur son ID"""
    colors = [
        "#3b82f6",  # Blue
        "#10b981",  # Green
        "#f59e0b",  # Yellow
        "#ef4444",  # Red
        "#8b5cf6",  # Purple
        "#06b6d4",  # Cyan
        "#84cc16",  # Lime
        "#f97316",  # Orange
        "#ec4899",  # Pink
        "#6b7280",  # Gray
    ]
    return colors[project_id % len(colors)]


# Sauvegarder la méthode originale avant l'override
original_index = admin.site.index
# Override de la méthode index du site admin
admin.site.index = admin_index_view


@admin_required
def users_list(request):
    """Vue pour lister tous les utilisateurs avec leurs groupes"""
    users = User.objects.all().prefetch_related("groups").order_by("username")

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    context = {
        "users": users,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "admin/users_list.html", context)


@admin_required
def user_edit(request, user_id):
    """Vue pour modifier les groupes d'un utilisateur"""
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        # Récupérer les groupes sélectionnés
        selected_groups = request.POST.getlist("groups")

        # Récupérer les objets Group
        groups = Group.objects.filter(name__in=selected_groups)

        # Mettre à jour les groupes de l'utilisateur
        user.groups.set(groups)

        messages.success(request, f"Groupes mis à jour pour l'utilisateur {user.username}.")
        return redirect("users_list")

    # Récupérer tous les groupes disponibles
    all_groups = Group.objects.all().order_by("name")
    user_groups = user.groups.all()

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    context = {
        "user": user,
        "all_groups": all_groups,
        "user_groups": user_groups,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "admin/user_edit.html", context)


@admin_required
def groups_info(request):
    """Vue pour afficher les informations sur les groupes et leurs permissions"""
    groups = Group.objects.all().prefetch_related("permissions").order_by("name")

    groups_info = []
    for group in groups:
        users_count = group.user_set.count()
        permissions_count = group.permissions.count()

        # Définir la description basée sur le nom du groupe
        description = ""
        if group.name == "Admin":
            description = "Accès complet à toutes les fonctionnalités, y compris l'administration Django"
        elif group.name == "Manager":
            description = "Gestion des tests, exécutions et tags. Lecture seule des projets (pas d'accès admin)"
        elif group.name == "Viewer":
            description = "Accès en lecture seule uniquement, ne peut pas modifier les données"

        groups_info.append(
            {"group": group, "description": description, "users_count": users_count, "permissions_count": permissions_count}
        )

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    context = {
        "groups_info": groups_info,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "admin/groups_info.html", context)


@admin_required
def groups_list(request):
    """Vue pour lister tous les groupes avec leurs utilisateurs"""
    groups = Group.objects.all().prefetch_related("permissions", "user_set").order_by("name")

    groups_info = []
    for group in groups:
        users_count = group.user_set.count()
        permissions_count = group.permissions.count()

        # Définir la description basée sur le nom du groupe
        description = ""
        if group.name == "Admin":
            description = "Accès complet à toutes les fonctionnalités, y compris l'administration Django"
        elif group.name == "Manager":
            description = "Gestion des tests, exécutions et tags. Lecture seule des projets (pas d'accès admin)"
        elif group.name == "Viewer":
            description = "Accès en lecture seule uniquement, ne peut pas modifier les données"

        groups_info.append(
            {"group": group, "description": description, "users_count": users_count, "permissions_count": permissions_count}
        )

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    context = {
        "groups_info": groups_info,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "admin/groups_list.html", context)


@admin_required
@require_http_methods(["POST"])
def user_toggle_active(request, user_id):
    """Vue pour activer/désactiver un utilisateur via AJAX"""
    user = get_object_or_404(User, id=user_id)

    # Ne pas permettre de désactiver le dernier superuser
    if user.is_superuser and User.objects.filter(is_superuser=True, is_active=True).count() <= 1:
        return JsonResponse({"error": "Impossible de désactiver le dernier superutilisateur actif."}, status=400)

    user.is_active = not user.is_active
    user.save()

    status = "activé" if user.is_active else "désactivé"
    messages.success(request, f"Utilisateur {user.username} {status}.")

    return JsonResponse({"success": True, "is_active": user.is_active, "message": f"Utilisateur {status}"})


@can_manage_tags
@require_http_methods(["POST"])
def update_tag_color(request):
    """Modifier la couleur d'un tag existant"""
    from testing.models import Tag

    tag_id = request.POST.get("tag_id")
    color = request.POST.get("color", "#3b82f6")

    if not tag_id:
        messages.error(request, "ID du tag requis.")
        return redirect("administration_dashboard") + "?section=tags"

    try:
        tag = Tag.objects.get(id=tag_id)
        old_color = tag.color

        # Vérifier si un autre tag du même projet utilise déjà cette couleur
        if Tag.objects.filter(project=tag.project, color=color).exclude(id=tag.id).exists():
            messages.error(request, "Cette couleur est déjà utilisée pour un autre tag de ce projet.")
            return redirect("administration_dashboard") + "?section=tags"

        # Modifier la couleur du tag
        tag.color = color
        tag.save()

        messages.success(request, f'Couleur du tag "{tag.name}" modifiée de {old_color} vers {color}.')

    except Tag.DoesNotExist:
        messages.error(request, "Tag introuvable.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la modification de la couleur : {str(e)}")

    return redirect("/administration/?section=tags")


@admin_required
def contexts_info(request):
    """Vue pour afficher les informations sur les contextes utilisateurs"""
    from .models import UserContext
    from .services.context_service import ContextService

    user_contexts = UserContext.objects.all().prefetch_related("projects", "user__groups").order_by("user__username")
    context_stats = ContextService.get_context_statistics()

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    context = {
        "user_contexts": user_contexts,
        "context_stats": context_stats,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "admin/contexts_info.html", context)


@admin_required
def user_contexts_list(request):
    """Vue pour lister tous les utilisateurs avec leurs contextes"""
    from .services.context_service import ContextService

    # Utilisateurs avec accès restreint (ont des projets spécifiques)
    users_with_restricted_access = (
        User.objects.filter(usercontext__isnull=False, groups__name__in=["Manager", "Viewer"])
        .prefetch_related("groups", "usercontext__projects")
        .distinct()
    )

    # Utilisateurs sans contexte ou avec accès à tous les projets (Manager/Viewer uniquement)
    users_without_context = ContextService.get_users_without_context()

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    context = {
        "users_with_restricted_access": users_with_restricted_access,
        "users_without_context": users_without_context,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "admin/user_contexts_list.html", context)
