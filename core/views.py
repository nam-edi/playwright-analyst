"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

import calendar
import json
from datetime import datetime, timedelta

import requests

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from api.models import APIKey
from core.management.commands.import_playwright import Command
from integrations.models import CIConfiguration, GitHubConfiguration, GitLabConfiguration
from projects.models import Project, ProjectFeature
from testing.models import Tag, Test, TestExecution, TestResult

from .permissions import admin_access_required, can_manage_projects, can_modify_data, manager_required
from .services.ci_services import CIServiceError, fetch_test_results_by_job_id, get_ci_service
from .services.context_service import ContextService


def filter_test_results_by_visible_tags(test_results, project):
    """
    Filtre les résultats de tests pour ne garder que ceux avec des tags visibles
    (exclut les tests qui n'ont que des tags exclus)
    """
    filtered_results = []
    for result in test_results:
        # Récupérer les tags visibles du test (excluant les tags exclus du projet)
        test_visible_tags = result.test.tags.exclude(id__in=project.excluded_tags.values_list("id", flat=True))
        # Garder le test s'il a des tags visibles OU s'il n'a aucun tag
        if test_visible_tags.exists() or not result.test.tags.exists():
            filtered_results.append(result)
    return filtered_results


def get_selected_project_for_user(request):
    """
    Fonction utilitaire pour récupérer le projet sélectionné en tenant compte du contexte utilisateur.
    Retourne (selected_project, projects, auto_selected) où projects sont tous les projets accessibles.
    """
    selected_project = None
    project_id = request.session.get("selected_project_id")
    auto_selected = False

    # Récupérer tous les projets accessibles à l'utilisateur
    projects = ContextService.get_user_accessible_projects(request.user)
    projects_count = projects.count()

    # Si un seul projet est accessible, le sélectionner automatiquement
    if projects_count == 1:
        selected_project = projects.first()
        request.session["selected_project_id"] = selected_project.id
        auto_selected = True
    elif project_id:
        try:
            # Vérifier que l'utilisateur peut accéder à ce projet
            selected_project = projects.get(id=project_id)
        except Project.DoesNotExist:
            # Nettoyer la session si le projet n'existe pas ou n'est pas accessible
            if "selected_project_id" in request.session:
                del request.session["selected_project_id"]

    return selected_project, projects, auto_selected


class CustomLoginView(LoginView):
    """Vue de connexion personnalisée qui ajoute un message de bienvenue"""

    template_name = "registration/login.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        """Ajouter un message de succès après connexion réussie"""
        response = super().form_valid(form)
        user = form.get_user()
        username = user.first_name if user.first_name else user.username
        messages.success(
            self.request, f"Bienvenue, {username} ! Vous êtes connecté et avez accès à toutes les fonctionnalités."
        )
        return response

    def form_invalid(self, form):
        """Gérer les erreurs de connexion avec des messages détaillés"""
        # Vérifier si l'utilisateur existe
        username = self.request.POST.get("username", "")
        if username:
            try:
                User.objects.get(username=username)
                messages.error(
                    self.request,
                    f'Utilisateur trouvé mais mot de passe incorrect pour "{username}". Veuillez vérifier votre mot de passe.',
                )
            except User.DoesNotExist:
                messages.error(
                    self.request,
                    f'Aucun utilisateur trouvé avec le nom "{username}". Veuillez vérifier votre nom d\'utilisateur.',
                )
        else:
            messages.error(self.request, "Veuillez remplir tous les champs requis.")

        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """Vue de déconnexion personnalisée qui nettoie la session du projet sélectionné"""

    next_page = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        """Nettoyer la session avant la déconnexion"""
        # Supprimer le projet sélectionné de la session
        if "selected_project_id" in request.session:
            del request.session["selected_project_id"]

        response = super().dispatch(request, *args, **kwargs)

        # Ajouter un message de confirmation
        messages.info(request, "Vous avez été déconnecté avec succès.")

        return response


@admin_access_required
def admin_redirect(request):
    """Vue pour rediriger vers l'administration Django avec authentification requise"""
    return redirect("/admin/")


def home(request):
    # Si l'utilisateur n'est pas connecté, rediriger vers la page de login
    if not request.user.is_authenticated:
        return redirect("login")

    latest_execution = None
    latest_execution_stats = None
    success_rate_data = []
    duration_data = []
    heatmap_data = []
    tags_map_data = []
    tags_links_data = []

    # Le projet sélectionné est géré par le context processor
    # Récupérer depuis le contexte global
    selected_project = None
    if hasattr(request, "_cached_user"):
        # Le context processor a déjà été exécuté
        pass

    # Utiliser la session pour récupérer le projet sélectionné
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
            # Vérifier que l'utilisateur peut accéder à ce projet
            accessible_projects = ContextService.get_user_accessible_projects(request.user)
            if not accessible_projects.filter(id=selected_project.id).exists():
                selected_project = None
                del request.session["selected_project_id"]
        except Project.DoesNotExist:
            selected_project = None
            if "selected_project_id" in request.session:
                del request.session["selected_project_id"]

    if selected_project:
        # Récupérer la dernière exécution du projet
        latest_execution = selected_project.executions.order_by("-start_time").first()

        if latest_execution:
            # Calculer les statistiques de la dernière exécution selon la nouvelle logique
            # Filtrer pour exclure les tests qui n'ont que des tags exclus
            all_results = latest_execution.test_results.exclude(expected_status="skipped")
            filtered_results = filter_test_results_by_visible_tags(all_results, selected_project)

            latest_execution_stats = {
                "passed": len([r for r in filtered_results if r.status == "passed"]),
                "failed": len([r for r in filtered_results if r.status in ["failed", "unexpected"]]),
                "skipped": len([r for r in filtered_results if r.status == "skipped"]),
                "flaky": len(
                    [r for r in filtered_results if r.retry > 0 and r.status == "passed"]
                ),  # Tests avec retries qui sont passés
                "total": len(filtered_results),
            }

            # Récupérer les tests instables (flaky) de la dernière exécution avec détails
            flaky_tests = []
            flaky_results = [r for r in filtered_results if r.retry > 0 and r.status == "passed"]
            for result in flaky_results:
                flaky_tests.append(
                    {
                        "test": result.test,
                        "retry_count": result.retry,
                        "duration": result.duration,
                        "file_path": result.test.file_path,
                        "title": result.test.title,
                        "test_id": result.test.test_id,
                    }
                )

            # Trier par nombre de retries décroissant
            flaky_tests.sort(key=lambda x: x["retry_count"], reverse=True)
        else:
            flaky_tests = []

        # Données pour le graphique d'évolution du taux de réussite (20 dernières exécutions)
        recent_executions = selected_project.executions.order_by("-start_time")[:20]
        for execution in recent_executions:
            total_tests = execution.test_results.exclude(expected_status="skipped").count()
            passed_tests = execution.test_results.filter(status="passed").count()
            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            success_rate_data.append(round(success_rate, 1))

        # Données pour le graphique des durées d'exécution (20 dernières exécutions)
        for execution in recent_executions:
            duration_data.append(execution.duration)

        # Données pour la heatmap (mois en cours)
        now = timezone.localtime(timezone.now())  # Convertir en heure locale
        current_year = now.year
        current_month = now.month

        # Premier et dernier jour du mois en cours en heure locale
        first_day_of_month = timezone.make_aware(datetime(current_year, current_month, 1))
        last_day_of_month = timezone.make_aware(
            datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1], 23, 59, 59)
        )

        # Récupérer le nombre d'exécutions par jour pour le mois en cours
        # Utiliser TruncDate avec timezone pour convertir en date locale
        executions_by_day = (
            selected_project.executions.filter(start_time__gte=first_day_of_month, start_time__lte=last_day_of_month)
            .annotate(day=TruncDate("start_time", tzinfo=timezone.get_current_timezone()))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        # Créer un dictionnaire pour un accès rapide
        execution_counts = {item["day"].strftime("%Y-%m-%d"): item["count"] for item in executions_by_day}

        # Générer les données pour tous les jours du mois en cours
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        for day in range(1, days_in_month + 1):
            date = datetime(current_year, current_month, day).date()
            date_str = date.strftime("%Y-%m-%d")
            count = execution_counts.get(date_str, 0)
            heatmap_data.append({"date": date_str, "count": count})

    # Données pour la cartographie des tags (seulement si un projet est sélectionné et la feature activée)
    tags_map_data = []
    tags_links_data = []
    if selected_project and selected_project.is_feature_enabled("tags_mapping"):
        # Récupérer tous les tags du projet avec les statistiques des tests (excluant les tags exclus)
        tags_stats = (
            Tag.objects.filter(test__project=selected_project)
            .exclude(id__in=selected_project.excluded_tags.values_list("id", flat=True))
            .distinct()
            .annotate(total_tests=Count("test", distinct=True))
            .order_by("name")
        )

        tag_nodes = {}
        for tag in tags_stats:
            # Récupérer les statistiques détaillées pour ce tag
            tag_tests = Test.objects.filter(project=selected_project, tags=tag)

            # Calculer les statistiques basées sur les derniers résultats de chaque test
            passed_count = 0
            failed_count = 0
            skipped_count = 0
            flaky_count = 0
            total_count = 0

            for test in tag_tests:
                latest_result = test.get_latest_result()
                if latest_result and latest_result.expected_status != "skipped":
                    total_count += 1
                    if latest_result.status == "passed":
                        passed_count += 1
                    elif latest_result.status in ["failed", "unexpected"]:
                        failed_count += 1
                    elif latest_result.status == "skipped":
                        skipped_count += 1
                    elif latest_result.status == "flaky":
                        flaky_count += 1

            # Calculer le taux de réussite
            success_rate = (passed_count / total_count * 100) if total_count > 0 else 0

            tag_data = {
                "id": tag.id,
                "name": tag.name,
                "color": tag.color,
                "total_tests": total_count,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "flaky_count": flaky_count,
                "success_rate": round(success_rate, 1),
            }

            tags_map_data.append(tag_data)
            tag_nodes[tag.id] = tag_data

        # Calculer les liens entre les tags (tests partagés)

        for i, tag1 in enumerate(tags_stats):
            for tag2 in tags_stats[i + 1 :]:  # Éviter les doublons
                # Compter les tests qui ont les deux tags
                shared_tests = Test.objects.filter(project=selected_project, tags=tag1).filter(tags=tag2).count()

                if shared_tests > 0:
                    tags_links_data.append({"source": tag1.id, "target": tag2.id, "value": shared_tests})

    # Récupérer tous les projets accessibles à l'utilisateur pour la liste déroulante
    ContextService.get_user_accessible_projects(request.user)

    context = {
        "latest_execution": latest_execution,
        "latest_execution_stats": latest_execution_stats,
        "flaky_tests": flaky_tests if selected_project and latest_execution else [],
        "recent_executions": recent_executions if selected_project else [],
        "success_rate_data": success_rate_data,
        "duration_data": duration_data,
        "heatmap_data": heatmap_data,
        "tags_map_data": tags_map_data,
        "tags_links_data": tags_links_data,
    }

    return render(request, "home.html", context)


@login_required
def select_project(request):
    """Vue pour sélectionner un projet"""
    if request.method == "POST":
        project_id = request.POST.get("project_id")

        if project_id:
            try:
                # Vérifier que l'utilisateur peut accéder à ce projet
                accessible_projects = ContextService.get_user_accessible_projects(request.user)
                project = accessible_projects.get(id=project_id)
                request.session["selected_project_id"] = project.id
                messages.success(request, f'Projet "{project.name}" sélectionné')

                # Retourner la réponse HTMX avec redirection
                response = HttpResponse()
                response["HX-Redirect"] = request.META.get("HTTP_REFERER", "/")
                return response

            except Project.DoesNotExist:
                messages.error(request, "Projet introuvable")
        else:
            # Si aucun projet sélectionné, on nettoie la session
            if "selected_project_id" in request.session:
                del request.session["selected_project_id"]
            messages.success(request, "Aucun projet sélectionné")

            response = HttpResponse()
            response["HX-Redirect"] = request.META.get("HTTP_REFERER", "/")
            return response

    return redirect("home")


def tests_list(request):
    """Vue pour afficher la liste des tests du projet sélectionné"""
    # Si l'utilisateur n'est pas connecté, afficher la page de login
    if not request.user.is_authenticated:
        return render(request, "registration/login.html")
    # ...existing code...
    # Récupérer le projet sélectionné et les projets accessibles
    selected_project, projects, auto_selected = get_selected_project_for_user(request)

    if not selected_project:
        messages.warning(request, "Veuillez sélectionner un projet pour voir les tests.")
        return redirect("home")

    # Récupérer les TESTS du projet sélectionné (pas les résultats)
    tests = (
        Test.objects.filter(project=selected_project)
        .prefetch_related("tags", "results__execution")
        .order_by("file_path", "line")
    )

    # Filtres basés sur les TESTS
    search = request.GET.get("search", "")
    tag_filter = request.GET.getlist("tags")

    if search:
        tests = tests.filter(title__icontains=search)

    if tag_filter:
        tests = tests.filter(tags__id__in=tag_filter).distinct()

    # Pagination
    paginator = Paginator(tests, 20)  # 20 tests par page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Tags disponibles pour les filtres (directement depuis les tests, excluant les tags exclus)
    available_tags_qs = (
        Tag.objects.filter(test__project=selected_project)
        .exclude(id__in=selected_project.excluded_tags.values_list("id", flat=True))
        .distinct()
    )
    available_tags = [{"id": tag.id, "name": tag.name, "color": tag.color} for tag in available_tags_qs]

    context = {
        "selected_project": selected_project,
        "projects": projects,
        "page_obj": page_obj,
        "tests": page_obj,
        "available_tags": available_tags,
        "search": search,
        "tag_filter": tag_filter,
    }

    # Si c'est une requête HTMX, retourner seulement le contenu des tests
    if request.headers.get("HX-Request"):
        return render(request, "cotton/tests-container.html", context)

    return render(request, "test/tests_list.html", context)


def test_detail(request, test_id):
    """Vue pour afficher les détails d'un test dans le panneau latéral"""
    test = get_object_or_404(Test, id=test_id)

    # Récupérer toutes les exécutions du test, triées par date décroissante (plus récent en premier)
    test_results = test.results.select_related("execution").order_by("-start_time")

    # Pagination pour les résultats
    paginator = Paginator(test_results, 10)  # 10 résultats par page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "test": test,
        "test_results": page_obj,
        "page_obj": page_obj,
    }

    return render(request, "cotton/test-detail-panel.html", context)


@can_modify_data
def update_test_comment(request, test_id):
    """Vue pour mettre à jour le commentaire d'un test via HTMX"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    test = get_object_or_404(Test, id=test_id)
    comment = request.POST.get("comment", "").strip()

    test.comment = comment
    test.save()

    # Retourner le fragment HTML mis à jour
    context = {"test": test}
    return render(request, "cotton/test-comment-fragment.html", context)


@can_modify_data
def update_test_result_status(request, result_id):
    """Vue pour mettre à jour le statut d'un résultat de test via HTMX"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    result = get_object_or_404(TestResult, id=result_id)
    new_status = request.POST.get("status", "").strip()

    # Vérifier que le nouveau statut est valide
    valid_statuses = [choice[0] for choice in TestResult.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({"error": "Statut invalide"}, status=400)

    result.status
    result.status = new_status
    result.save()

    # Retourner le fragment HTML mis à jour du badge de statut
    context = {"result": result}
    return render(request, "cotton/status-badge.html", context)


@can_modify_data
def update_execution_comment(request, execution_id):
    """Vue pour mettre à jour le commentaire d'une exécution via HTMX"""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    execution = get_object_or_404(TestExecution, id=execution_id)
    comment = request.POST.get("comment", "").strip()

    execution.comment = comment
    execution.save()

    # Retourner le fragment HTML mis à jour
    context = {"execution": execution}
    return render(request, "cotton/execution-comment-fragment.html", context)


def htmx_example(request):
    """Exemple de vue HTMX"""
    return HttpResponse(
        """
        <div class="p-4 bg-green-100 border border-green-400 text-green-700 rounded">
            <h4 class="font-bold">HTMX fonctionne !</h4>
            <p>Cette réponse a été chargée dynamiquement sans rechargement de page.</p>
            <p class="text-sm mt-2">Timestamp: <span class="font-mono">{}</span></p>
        </div>
    """.format(
            __import__("datetime").datetime.now().strftime("%H:%M:%S")
        )
    )


def executions_list(request):
    """Vue pour afficher la liste des exécutions du projet sélectionné"""
    # Si l'utilisateur n'est pas connecté, afficher la page de login
    if not request.user.is_authenticated:
        return render(request, "registration/login.html")
    # ...existing code...
    selected_project = None
    project_id = None
    if "selected_project_id" in request.session:
        project_id = request.session["selected_project_id"]
    if project_id:
        try:
            selected_project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            # Nettoyer la session/cookie si le projet n'existe pas
            if request.user.is_authenticated and "selected_project_id" in request.session:
                del request.session["selected_project_id"]

    if not selected_project:
        messages.warning(request, "Veuillez sélectionner un projet pour voir les exécutions.")
        return redirect("home")

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer les exécutions du projet sélectionné, triées par date décroissante
    executions = TestExecution.objects.filter(project=selected_project).order_by("-start_time")

    # Filtres par date
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    date_preset = request.GET.get("date_preset")

    # Appliquer les filtres de date prédéfinis
    now = timezone.now()
    if date_preset == "current_week":
        # Début de la semaine (lundi)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        executions = executions.filter(start_time__gte=start_of_week)
        date_from = start_of_week.strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")
    elif date_preset == "current_month":
        # Début du mois
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        executions = executions.filter(start_time__gte=start_of_month)
        date_from = start_of_month.strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")
    elif date_from or date_to:
        # Filtres de date personnalisés
        if date_from:
            try:
                date_from_parsed = datetime.strptime(date_from, "%Y-%m-%d")
                date_from_parsed = timezone.make_aware(date_from_parsed)
                executions = executions.filter(start_time__gte=date_from_parsed)
            except ValueError:
                messages.error(request, "Format de date de début invalide.")
                date_from = None

        if date_to:
            try:
                date_to_parsed = datetime.strptime(date_to, "%Y-%m-%d")
                # Ajouter 23:59:59 pour inclure toute la journée
                date_to_parsed = date_to_parsed.replace(hour=23, minute=59, second=59)
                date_to_parsed = timezone.make_aware(date_to_parsed)
                executions = executions.filter(start_time__lte=date_to_parsed)
            except ValueError:
                messages.error(request, "Format de date de fin invalide.")
                date_to = None

    # Ajouter les statistiques pour chaque exécution
    executions_with_stats = []
    for execution in executions:
        # Calculer les statistiques selon la nouvelle logique avec retries
        # Filtrer pour exclure les tests qui n'ont que des tags exclus
        all_test_results = TestResult.objects.filter(execution=execution).exclude(expected_status="skipped")
        filtered_test_results = filter_test_results_by_visible_tags(all_test_results, selected_project)

        pass_count = len([r for r in filtered_test_results if r.status == "passed"])
        fail_count = len([r for r in filtered_test_results if r.status in ["failed", "unexpected"]])
        skip_count = len([r for r in filtered_test_results if r.status == "skipped"])
        total_count = len(filtered_test_results)

        # Récupérer les tests avec commentaires pour cette exécution
        tests_with_comments = []
        test_ids_in_execution = [r.test.id for r in filtered_test_results]
        for test in Test.objects.filter(id__in=test_ids_in_execution, comment__isnull=False).exclude(comment=""):
            tests_with_comments.append({"title": test.title, "comment": test.comment})

        executions_with_stats.append(
            {
                "execution": execution,
                "pass_count": pass_count,
                "fail_count": fail_count,
                "skip_count": skip_count,
                "total_count": total_count,
                "tests_with_comments": tests_with_comments,
            }
        )

    # Pagination
    paginator = Paginator(executions_with_stats, 20)  # 20 exécutions par page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "selected_project": selected_project,
        "projects": projects,
        "page_obj": page_obj,
        "executions_with_stats": page_obj,
        "date_from": date_from,
        "date_to": date_to,
        "date_preset": date_preset,
    }

    return render(request, "execution/executions_list.html", context)


def execution_detail(request, execution_id):
    """Vue pour afficher le détail d'une exécution avec tous ses tests"""
    # Si l'utilisateur n'est pas connecté, afficher la page de login
    if not request.user.is_authenticated:
        return render(request, "registration/login.html")
    # ...existing code...
    execution = get_object_or_404(TestExecution, id=execution_id)
    selected_project = None
    project_id = None
    if "selected_project_id" in request.session:
        project_id = request.session["selected_project_id"]
    if project_id:
        try:
            selected_project = Project.objects.get(id=project_id)
            if execution.project != selected_project:
                messages.error(request, "Cette exécution n'appartient pas au projet sélectionné.")
                return redirect("executions_list")
        except Project.DoesNotExist:
            # Nettoyer la session/cookie si le projet n'existe pas
            if request.user.is_authenticated and "selected_project_id" in request.session:
                del request.session["selected_project_id"]

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    # Récupérer tous les résultats de tests pour cette exécution
    test_results = TestResult.objects.filter(execution=execution).select_related("test").prefetch_related("test__tags")

    # Filtrer les résultats de tests qui n'ont que des tags exclus
    excluded_tag_ids = set(execution.project.excluded_tags.values_list("id", flat=True))
    filtered_test_results = []

    for result in test_results:
        test_tag_ids = set(result.test.tags.values_list("id", flat=True))

        # Si le test n'a aucun tag, l'inclure
        if not test_tag_ids:
            filtered_test_results.append(result)
        # Si le test a au moins un tag visible (non exclu), l'inclure
        elif not test_tag_ids.issubset(excluded_tag_ids):
            filtered_test_results.append(result)
        # Sinon, le test n'a que des tags exclus, donc l'exclure

    test_results = filtered_test_results

    # Ajouter l'information du statut de la dernière exécution pour chaque test
    # Seulement si la feature "evolution_tracking" est activée
    evolution_tracking_enabled = execution.project.is_feature_enabled("evolution_tracking")

    test_results_with_previous_status = []
    for result in test_results:
        if evolution_tracking_enabled:
            # Récupérer le dernier résultat de ce test (excluant l'exécution courante)
            previous_result = (
                TestResult.objects.filter(test=result.test, execution__start_time__lt=execution.start_time)
                .order_by("-execution__start_time")
                .first()
            )

            # Ajouter l'information au résultat
            result.previous_status = previous_result.status if previous_result else None
            result.was_ko_before = (
                previous_result and previous_result.status in ["failed", "unexpected"] if previous_result else False
            )

            # Déterminer l'évolution du statut (amélioration, régression, stable)
            if previous_result:
                current_is_success = result.status == "passed"
                previous_is_success = previous_result.status == "passed"

                if current_is_success and not previous_is_success:
                    result.status_evolution = "improved"  # Amélioration
                elif not current_is_success and previous_is_success:
                    result.status_evolution = "regressed"  # Régression
                else:
                    result.status_evolution = "stable"  # Stable
            else:
                result.status_evolution = "new"  # Nouveau test
        else:
            # Si la feature est désactivée, ne pas calculer l'évolution
            result.previous_status = None
            result.was_ko_before = False
            result.status_evolution = None

        test_results_with_previous_status.append(result)

    test_results = test_results_with_previous_status

    # Filtres
    status_filter = request.GET.get("status", "")
    search = request.GET.get("search", "")
    tag_filter = request.GET.get("tag", "")
    evolution_filter = request.GET.get("evolution", "")
    sort_by = request.GET.get("sort", "test_title")  # Par défaut tri par titre du test

    # Récupérer tous les tags disponibles pour cette exécution (excluant les tags exclus)
    available_tags = (
        Tag.objects.filter(test__results__execution=execution)
        .exclude(id__in=execution.project.excluded_tags.values_list("id", flat=True))
        .distinct()
        .order_by("name")
    )

    # Appliquer le filtre de statut
    if status_filter:
        if status_filter == "passed":
            test_results = [r for r in test_results if r.status == "passed"]
        elif status_filter == "failed":
            test_results = [r for r in test_results if r.status in ["failed", "unexpected"]]
        elif status_filter == "skipped":
            test_results = [r for r in test_results if r.status == "skipped"]
        elif status_filter == "flaky":
            test_results = [r for r in test_results if r.status == "flaky"]

    # Appliquer le filtre de recherche
    if search:
        test_results = [r for r in test_results if search.lower() in r.test.title.lower()]

    # Appliquer le filtre par tag
    if tag_filter:
        test_results = [r for r in test_results if r.test.tags.filter(name=tag_filter).exists()]

    # Appliquer le filtre par évolution
    if evolution_filter:
        test_results = [r for r in test_results if hasattr(r, "status_evolution") and r.status_evolution == evolution_filter]

    # Appliquer le tri
    if sort_by == "duration_asc":
        test_results = sorted(test_results, key=lambda x: x.duration)
    elif sort_by == "duration_desc":
        test_results = sorted(test_results, key=lambda x: x.duration, reverse=True)
    elif sort_by == "status":
        test_results = sorted(test_results, key=lambda x: (x.status, x.test.title))
    elif sort_by == "file_path":
        test_results = sorted(test_results, key=lambda x: (x.test.file_path, x.test.line))
    else:  # test_title par défaut
        test_results = sorted(test_results, key=lambda x: x.test.title)

    # Calculer les statistiques globales en utilisant les résultats filtrés (sans tags exclus)
    # Récupérer tous les résultats pour les statistiques, mais filtrés
    all_results_query = TestResult.objects.filter(execution=execution).exclude(expected_status="skipped")
    excluded_tag_ids = list(execution.project.excluded_tags.values_list("id", flat=True))

    # Filtrer les résultats pour exclure ceux qui n'ont que des tags exclus
    all_results_filtered = []
    for result in all_results_query.select_related("test").prefetch_related("test__tags"):
        test_tag_ids = set(result.test.tags.values_list("id", flat=True))
        # Si le test n'a aucun tag, l'inclure
        if not test_tag_ids:
            all_results_filtered.append(result)
        # Si le test a au moins un tag visible (non exclu), l'inclure
        elif not test_tag_ids.issubset(excluded_tag_ids):
            all_results_filtered.append(result)

    # Calculer les statistiques à partir des résultats filtrés
    flaky_count = len([r for r in all_results_filtered if r.retry > 0 and r.status == "passed"])
    passed_count = len([r for r in all_results_filtered if r.status == "passed"])
    failed_count = len([r for r in all_results_filtered if r.status in ["failed", "unexpected"]])
    skipped_count = len([r for r in all_results_filtered if r.status == "skipped"])
    total_count = len(all_results_filtered)

    stats = {
        "total": total_count,
        "passed": passed_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "flaky": flaky_count,
    }

    # Calculer les statistiques d'évolution seulement si la feature est activée
    evolution_stats = {}
    if evolution_tracking_enabled:
        evolution_stats = {
            "improved": len([r for r in test_results if hasattr(r, "status_evolution") and r.status_evolution == "improved"]),
            "regressed": len(
                [r for r in test_results if hasattr(r, "status_evolution") and r.status_evolution == "regressed"]
            ),
            "stable": len([r for r in test_results if hasattr(r, "status_evolution") and r.status_evolution == "stable"]),
            "new": len([r for r in test_results if hasattr(r, "status_evolution") and r.status_evolution == "new"]),
        }

    # Calculer la répartition des échecs par tag
    # Récupérer les résultats échoués en excluant les tests qui n'ont que des tags exclus
    failed_results_query = TestResult.objects.filter(execution=execution, status__in=["failed", "unexpected"]).exclude(
        expected_status="skipped"
    )

    # Filtrer pour exclure les tests qui n'ont que des tags exclus
    failed_results = []
    for result in failed_results_query:
        test_visible_tags = result.test.tags.exclude(id__in=execution.project.excluded_tags.values_list("id", flat=True))
        if test_visible_tags.exists():
            failed_results.append(result)

    failed_results_ids = [r.id for r in failed_results]
    failed_results_queryset = TestResult.objects.filter(id__in=failed_results_ids)

    # Récupérer les tags des tests qui ont échoué avec leur nombre d'échecs (excluant les tags exclus)
    tag_failure_stats = []
    for tag in (
        Tag.objects.filter(test__results__in=failed_results_queryset)
        .exclude(id__in=execution.project.excluded_tags.values_list("id", flat=True))
        .distinct()
    ):
        failed_count = failed_results_queryset.filter(test__tags=tag).count()
        # Calculer le total en comptant tous les résultats de l'exécution pour ce tag (avec tags visibles)
        total_results_for_tag = TestResult.objects.filter(execution=execution, test__tags=tag).exclude(
            expected_status="skipped"
        )
        # Filtrer pour ne garder que ceux avec des tags visibles
        total_count = 0
        for result in total_results_for_tag:
            test_visible_tags = result.test.tags.exclude(id__in=execution.project.excluded_tags.values_list("id", flat=True))
            if test_visible_tags.exists():
                total_count += 1

        failure_rate = (failed_count / total_count * 100) if total_count > 0 else 0

        tag_failure_stats.append(
            {"tag": tag, "failed_count": failed_count, "total_count": total_count, "failure_rate": round(failure_rate, 1)}
        )

    # Trier par nombre d'échecs décroissant
    tag_failure_stats.sort(key=lambda x: x["failed_count"], reverse=True)

    # Pagination
    paginator = Paginator(test_results, 50)  # 50 résultats par page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "execution": execution,
        "selected_project": selected_project or execution.project,
        "projects": projects,
        "page_obj": page_obj,
        "test_results": page_obj,
        "stats": stats,
        "evolution_stats": evolution_stats,
        "evolution_tracking_enabled": evolution_tracking_enabled,
        "tag_failure_stats": tag_failure_stats,
        "status_filter": status_filter,
        "search": search,
        "tag_filter": tag_filter,
        "evolution_filter": evolution_filter,
        "sort_by": sort_by,
        "available_tags": available_tags,
    }

    return render(request, "execution/execution_detail.html", context)


@manager_required
def execution_delete(request, execution_id):
    """Vue pour supprimer une exécution (uniquement pour Admin et Manager)"""
    execution = get_object_or_404(TestExecution, id=execution_id)

    # Vérifier que l'utilisateur a accès au projet de cette exécution
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
            if execution.project != selected_project:
                messages.error(request, "Cette exécution n'appartient pas au projet sélectionné.")
                return redirect("executions_list")
        except Project.DoesNotExist:
            if "selected_project_id" in request.session:
                del request.session["selected_project_id"]

    if request.method == "POST":
        project_name = execution.project.name
        execution_date = execution.start_time.strftime("%d/%m/%Y à %H:%M")

        # Supprimer l'exécution (les résultats de tests seront supprimés automatiquement via CASCADE)
        execution.delete()

        messages.success(
            request, f"L'exécution du {execution_date} pour le projet '{project_name}' a été supprimée avec succès."
        )
        return redirect("executions_list")

    # Si GET, rediriger vers la page de détail
    return redirect("execution_detail", execution_id=execution_id)


@can_modify_data
def upload_json(request):
    """Vue pour afficher la page d'upload de fichiers JSON"""
    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = Project.objects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    # Récupérer tous les projets pour le header et le sélecteur
    projects = Project.objects.all()

    context = {
        "selected_project": selected_project,
        "projects": projects,
    }

    return render(request, "import/upload_json.html", context)


@can_modify_data
def process_json_upload(request):
    """Vue pour traiter l'upload et l'importation d'un fichier JSON"""
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    # Vérifier qu'un projet est sélectionné ou fourni
    project_id = request.POST.get("project_id")
    if not project_id and "selected_project_id" in request.session:
        project_id = request.session["selected_project_id"]

    if not project_id:
        return JsonResponse({"error": "Aucun projet sélectionné"}, status=400)

    # Vérifier que le projet existe
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Projet introuvable"}, status=404)

    # Vérifier qu'un fichier est fourni
    if "json_file" not in request.FILES:
        return JsonResponse({"error": "Aucun fichier fourni"}, status=400)

    uploaded_file = request.FILES["json_file"]

    # Vérifier l'extension du fichier
    if not uploaded_file.name.endswith(".json"):
        return JsonResponse({"error": "Le fichier doit avoir l'extension .json"}, status=400)

    try:
        # Lire et parser le JSON
        file_content = uploaded_file.read().decode("utf-8")
        data = json.loads(file_content)

        # Traiter l'importation
        execution = import_json_data(project, data)

        return JsonResponse(
            {
                "success": True,
                "message": f'Importation réussie ! Exécution créée : {execution.start_time.strftime("%d/%m/%Y à %H:%M")}',
                "execution_id": execution.id,
                "redirect_url": f"/execution/{execution.id}/",
            }
        )

    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"Fichier JSON invalide : {str(e)}"}, status=400)
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de l'importation : {str(e)}"}, status=500)


def import_json_data(project, data):
    """Fonction pour importer les données JSON - utilise exactement la même logique que la commande Django"""

    # Vérifier que les données sont bien un dictionnaire
    if not isinstance(data, dict):
        raise ValueError(f"Les données JSON doivent être un objet (dictionnaire), reçu: {type(data)}")

    # Vérifier que les champs requis sont présents
    if "suites" not in data:
        raise ValueError("Les données JSON doivent contenir un champ 'suites'")

    # Créer une instance de la commande Django et utiliser sa logique
    command = Command()

    # Créer l'exécution de test
    execution = command.create_test_execution(project, data)

    # Traiter les suites et tests avec la logique existante qui fonctionne
    test_count = 0
    result_count = 0

    for suite in data.get("suites", []):
        test_count_suite, result_count_suite = command.process_suite(suite, execution)
        test_count += test_count_suite
        result_count += result_count_suite

    return execution


@can_modify_data
def fetch_from_ci(request, project_id):
    """Vue pour récupérer automatiquement les résultats depuis la CI"""
    project = get_object_or_404(Project, id=project_id)

    # Définir ce projet comme sélectionné dans la session
    if request.user.is_authenticated:
        request.session["selected_project_id"] = project.id

    # Récupérer tous les projets pour le header
    if request.user.is_authenticated:
        projects = Project.objects.filter(created_by=request.user).order_by("name")
    else:
        projects = Project.objects.all().order_by("name")

    if not project.has_ci_configuration():
        messages.error(request, "Ce projet n'a pas de configuration CI.")
        return redirect("/administration/?section=import")

    if request.method == "GET":
        # Afficher le formulaire de sélection
        context = {
            "project": project,
            "projects": projects,  # Pour le sélecteur dans le header
            "selected_project": project,  # Pour la sélection dans le header
            "ci_provider": project.get_ci_provider(),
            "ci_config": project.get_ci_config_details(),
        }
        return render(request, "import/fetch_from_ci.html", context)

    elif request.method == "POST":
        job_id = request.POST.get("job_id", "").strip()

        if not job_id:
            messages.error(request, "Vous devez spécifier un Job ID.")
            return redirect("fetch_from_ci", project_id=project_id)

        try:
            # Récupérer depuis le job spécifique
            json_data = fetch_test_results_by_job_id(project, job_id)
            source_info = f"Job ID: {job_id}"

            if not json_data:
                messages.error(request, "Aucun résultat trouvé.")
                return redirect("fetch_from_ci", project_id=project_id)

            # Importer les données JSON
            execution = import_json_data(project, json_data)

            messages.success(
                request, f"Résultats importés avec succès depuis la CI ({source_info}). " f"Exécution créée: {execution}"
            )

            return redirect("execution_detail", execution_id=execution.id)

        except CIServiceError as e:
            messages.error(request, f"Erreur CI: {e}")
            return redirect("fetch_from_ci", project_id=project_id)
        except ValueError as e:
            messages.error(request, f"Erreur de format des données: {e}")
            return redirect("fetch_from_ci", project_id=project_id)
        except Exception as e:
            messages.error(request, f"Erreur lors de l'import: {e}")
            return redirect("fetch_from_ci", project_id=project_id)

    return HttpResponseNotAllowed(["GET", "POST"])


@manager_required
def project_features(request, project_id):
    """Vue pour gérer les features d'un projet"""
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        # Traiter la mise à jour des features
        for feature_key, feature_name in ProjectFeature.FEATURE_CHOICES:
            is_enabled = request.POST.get(f"feature_{feature_key}") == "on"

            feature, created = ProjectFeature.objects.get_or_create(
                project=project, feature_key=feature_key, defaults={"is_enabled": is_enabled}
            )

            if not created and feature.is_enabled != is_enabled:
                feature.is_enabled = is_enabled
                feature.save()

        messages.success(request, f'Configuration des features mise à jour pour le projet "{project.name}".')
        return redirect("/administration/?section=projects")

    # Récupérer toutes les features du projet avec les valeurs par défaut
    project_features = {}
    for feature_key, feature_name in ProjectFeature.FEATURE_CHOICES:
        try:
            feature = project.features.get(feature_key=feature_key)
            project_features[feature_key] = {
                "name": feature_name,
                "is_enabled": feature.is_enabled,
                "default_value": ProjectFeature.get_default_value(feature_key),
            }
        except ProjectFeature.DoesNotExist:
            # Si la feature n'existe pas, utiliser la valeur par défaut
            default_value = ProjectFeature.get_default_value(feature_key)
            project_features[feature_key] = {"name": feature_name, "is_enabled": default_value, "default_value": default_value}

    # Récupérer tous les projets pour le header
    projects = Project.objects.all()

    context = {
        "project": project,
        "projects": projects,
        "project_features": project_features,
        "selected_project": project,  # Pour la cohérence avec les autres templates
    }

    return render(request, "project/project_features.html", context)


@can_manage_projects
def project_create(request):
    """Vue pour créer un nouveau projet"""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        ci_configuration_id = request.POST.get("ci_configuration_id", "").strip()

        # Gestion de la création de nouvelle configuration CI
        create_new_ci = request.POST.get("create_new_ci") == "on"
        ci_provider = request.POST.get("ci_provider", "").strip()
        ci_name = request.POST.get("ci_name", "").strip()

        if not name:
            messages.error(request, "Le nom du projet est obligatoire.")
        else:
            # Vérifier si un projet avec ce nom existe déjà
            if Project.objects.filter(name=name).exists():
                messages.error(request, f'Un projet avec le nom "{name}" existe déjà.')
            else:
                # Créer le projet (pour l'instant sans utilisateur, on peut ajouter ça plus tard)
                # Utiliser l'utilisateur actuel connecté ou un superuser
                user = request.user
                if not user.is_authenticated:
                    # Utiliser le premier superuser disponible
                    user = User.objects.filter(is_superuser=True).first()
                    if not user:
                        user = User.objects.filter(is_staff=True).first()
                    if not user:
                        # En dernier recours, utiliser le premier utilisateur
                        user = User.objects.first()
                        if not user:
                            messages.error(request, "Aucun utilisateur disponible pour créer le projet.")
                            return render(request, "project/project_create.html")

                # Récupérer ou créer la configuration CI
                ci_configuration = None
                if create_new_ci and ci_provider and ci_name:
                    try:
                        # Créer la configuration CI de base
                        ci_configuration = CIConfiguration.objects.create(name=ci_name, provider=ci_provider)

                        # Créer la configuration spécifique selon le provider
                        if ci_provider == "gitlab":
                            gitlab_url = request.POST.get("gitlab_url", "").strip()
                            project_id = request.POST.get("project_id", "").strip()
                            access_token = request.POST.get("access_token", "").strip()
                            job_name = request.POST.get("job_name", "").strip()
                            artifact_path = request.POST.get("artifact_path", "").strip()

                            if all([gitlab_url, project_id, access_token, job_name, artifact_path]):
                                GitLabConfiguration.objects.create(
                                    ci_config=ci_configuration,
                                    gitlab_url=gitlab_url,
                                    project_id=project_id,
                                    access_token=access_token,
                                    job_name=job_name,
                                    artifact_path=artifact_path,
                                )
                            else:
                                ci_configuration.delete()
                                messages.error(request, "Tous les champs GitLab sont obligatoires.")
                                ci_configuration = None

                        elif ci_provider == "github":
                            repository = request.POST.get("repository", "").strip()
                            github_token = request.POST.get("github_token", "").strip()
                            workflow_name = request.POST.get("workflow_name", "").strip()
                            artifact_name = request.POST.get("artifact_name", "").strip()
                            json_filename = request.POST.get("json_filename", "").strip()

                            if all([repository, github_token, workflow_name, artifact_name, json_filename]):
                                GitHubConfiguration.objects.create(
                                    ci_config=ci_configuration,
                                    repository=repository,
                                    access_token=github_token,
                                    workflow_name=workflow_name,
                                    artifact_name=artifact_name,
                                    json_filename=json_filename,
                                )
                            else:
                                ci_configuration.delete()
                                messages.error(request, "Tous les champs GitHub sont obligatoires.")
                                ci_configuration = None

                    except Exception as e:
                        messages.error(request, f"Erreur lors de la création de la configuration CI : {str(e)}")
                        if ci_configuration:
                            ci_configuration.delete()
                        ci_configuration = None

                elif ci_configuration_id:
                    try:
                        ci_configuration = CIConfiguration.objects.get(id=ci_configuration_id)
                    except CIConfiguration.DoesNotExist:
                        messages.warning(request, "Configuration CI introuvable, projet créé sans configuration CI.")

                if not messages.get_messages(request):  # Seulement si pas d'erreurs
                    project = Project.objects.create(
                        name=name, description=description, created_by=user, ci_configuration=ci_configuration
                    )

                    # Initialiser les features par défaut pour ce projet
                    for feature_key, feature_name in ProjectFeature.FEATURE_CHOICES:
                        ProjectFeature.objects.create(
                            project=project, feature_key=feature_key, is_enabled=ProjectFeature.get_default_value(feature_key)
                        )

                    success_msg = f'Projet "{name}" créé avec succès.'
                    if ci_configuration:
                        success_msg += f' Configuration CI "{ci_configuration.name}" associée.'
                    messages.success(request, success_msg)
                    return redirect("/administration/?section=projects")

    # Récupérer toutes les configurations CI disponibles

    ci_configurations = CIConfiguration.objects.all()

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
        "projects": projects,
        "selected_project": selected_project,
        "ci_configurations": ci_configurations,
    }

    return render(request, "project/project_create.html", context)


@can_manage_projects
def project_edit(request, project_id):
    """Vue pour modifier un projet"""
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        ci_configuration_id = request.POST.get("ci_configuration_id", "").strip()

        if not name:
            messages.error(request, "Le nom du projet est obligatoire.")
        else:
            # Vérifier si un autre projet avec ce nom existe déjà
            existing_project = Project.objects.filter(name=name).exclude(id=project.id).first()
            if existing_project:
                messages.error(request, f'Un autre projet avec le nom "{name}" existe déjà.')
            else:
                # Récupérer la configuration CI si fournie
                ci_configuration = None
                if ci_configuration_id:
                    try:
                        ci_configuration = CIConfiguration.objects.get(id=ci_configuration_id)
                    except CIConfiguration.DoesNotExist:
                        messages.warning(request, "Configuration CI introuvable, projet modifié sans configuration CI.")

                project.name = name
                project.description = description
                project.ci_configuration = ci_configuration
                project.save()

                messages.success(request, f'Projet "{name}" modifié avec succès.')
                return redirect("/administration/?section=projects")

    # Calculer les statistiques du projet
    executions_count = project.executions.count()
    tests_count = Test.objects.filter(project=project).count()
    features_count = ProjectFeature.objects.filter(project=project).count()

    # Récupérer toutes les configurations CI disponibles
    ci_configurations = CIConfiguration.objects.all()

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
        "project": project,
        "executions_count": executions_count,
        "tests_count": tests_count,
        "features_count": features_count,
        "ci_configurations": ci_configurations,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "project/project_edit.html", context)


@can_manage_projects
def project_delete(request, project_id):
    """Vue pour supprimer un projet"""
    project = get_object_or_404(Project, id=project_id)

    if request.method == "POST":
        project_name = project.name

        # Si le projet supprimé était sélectionné, nettoyer la session
        if "selected_project_id" in request.session and int(request.session["selected_project_id"]) == project.id:
            del request.session["selected_project_id"]

        project.delete()
        messages.success(request, f'Projet "{project_name}" supprimé avec succès.')
        return redirect("/administration/?section=projects")

    # Pour GET, afficher la page de confirmation
    return render(request, "project/project_edit.html", {"project": project, "delete_mode": True})


def ci_status_check(request, project_id):
    """Vue AJAX pour vérifier le statut de la configuration CI"""
    project = get_object_or_404(Project, id=project_id)

    if not project.has_ci_configuration():
        return JsonResponse({"status": "error", "message": "Aucune configuration CI trouvée"})

    try:
        ci_service = get_ci_service(project)
        if not ci_service:
            return JsonResponse({"status": "error", "message": "Service CI non disponible"})

        # Test basique de la configuration CI
        # Pour GitLab, on peut tester l'accès aux projets
        # Pour GitHub, on peut tester l'accès au repository
        if hasattr(ci_service, "base_url"):  # GitLab
            test_url = f"{ci_service.base_url}/api/v4/projects/{ci_service.project_id}"

            response = requests.get(test_url, headers=ci_service.headers, timeout=10)
            response.raise_for_status()
        else:  # GitHub
            test_url = f"https://api.github.com/repos/{ci_service.repository}"

            response = requests.get(test_url, headers=ci_service.headers, timeout=10)
            response.raise_for_status()

        return JsonResponse({"status": "success", "message": "Connexion réussie. Configuration CI valide."})

    except CIServiceError as e:
        return JsonResponse({"status": "error", "message": f"Erreur de connexion: {e}"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Erreur inattendue: {e}"})


@csrf_exempt
@require_http_methods(["POST"])
def api_upload_results(request, project_id):
    """
    API endpoint pour upload direct des résultats depuis la CI

    Accepte:
    - Content-Type: application/json (JSON dans le body)
    - Content-Type: multipart/form-data (fichier JSON)

    Paramètres optionnels:
    - api_key: Clé d'API pour authentification (en header X-API-Key ou en paramètre)
    """
    try:
        # Récupération du projet
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({"error": "Projet non trouvé", "status": "error"}, status=404)

        # Authentification par clé API
        api_key = request.headers.get("X-API-Key") or request.GET.get("api_key")
        if api_key:
            try:
                # APIKey déjà importé en haut du fichier
                api_key_obj = (
                    APIKey.objects.select_related("user").prefetch_related("projects").get(key=api_key, is_active=True)
                )

                # Vérifier l'expiration
                if api_key_obj.is_expired:
                    return JsonResponse({"error": "Clé API expirée", "status": "error"}, status=401)

                # Vérifier les permissions
                if not api_key_obj.can_upload:
                    return JsonResponse({"error": "Clé API sans permission d'upload", "status": "error"}, status=403)

                # Vérifier l'accès au projet
                if not api_key_obj.can_access_project(project):
                    return JsonResponse({"error": "Clé API sans accès à ce projet", "status": "error"}, status=403)

                # Mettre à jour la date de dernière utilisation
                api_key_obj.update_last_used()

            except APIKey.DoesNotExist:
                return JsonResponse({"error": "Clé API invalide", "status": "error"}, status=401)
        else:
            # Pour l'instant, on accepte les requêtes sans clé API
            # TODO: Rendre l'authentification obligatoire en production
            pass

        # Récupération des données JSON
        json_data = None

        if request.content_type == "application/json":
            # JSON dans le body de la requête
            try:
                json_data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError as e:
                return JsonResponse({"error": f"JSON invalide: {e}", "status": "error"}, status=400)

        elif request.content_type.startswith("multipart/form-data"):
            # Fichier JSON uploadé
            if "file" not in request.FILES:
                return JsonResponse({"error": 'Aucun fichier fourni. Utilisez le champ "file"', "status": "error"}, status=400)

            uploaded_file = request.FILES["file"]
            try:
                json_data = json.loads(uploaded_file.read().decode("utf-8"))
            except json.JSONDecodeError as e:
                return JsonResponse({"error": f"Fichier JSON invalide: {e}", "status": "error"}, status=400)
        else:
            return JsonResponse(
                {"error": "Content-Type non supporté. Utilisez application/json ou multipart/form-data", "status": "error"},
                status=400,
            )

        if not json_data:
            return JsonResponse({"error": "Aucune donnée JSON fournie", "status": "error"}, status=400)

        # Validation basique de la structure JSON Playwright
        if "suites" not in json_data:
            return JsonResponse({"error": 'Structure JSON invalide: "suites" manquant', "status": "error"}, status=400)

        # Import des données
        try:
            execution = import_json_data(project, json_data)

            return JsonResponse(
                {
                    "message": "Résultats importés avec succès",
                    "status": "success",
                    "execution_id": execution.id,
                    "execution_url": request.build_absolute_uri(f"/execution/{execution.id}/"),
                    "project": project.name,
                    "created_at": execution.created_at.isoformat(),
                },
                status=201,
            )

        except Exception as e:
            return JsonResponse({"error": f"Erreur lors de l'import: {e}", "status": "error"}, status=500)

    except Exception as e:
        return JsonResponse({"error": f"Erreur serveur: {e}", "status": "error"}, status=500)


@login_required
def api_documentation(request):
    """Page de documentation de l'API"""
    return render(request, "api/api_documentation.html")


def api_key_help(request):
    """Page d'aide pour la gestion des clés API"""
    return render(request, "api/api_key_help.html")


@login_required
def help_groups_permissions(request):
    """Page d'aide pour les groupes et permissions"""
    return render(request, "help/groups_permissions.html")


@login_required
def administration_dashboard(request):
    """Page principale d'administration avec menu latéral"""
    # Récupérer les projets accessibles par l'utilisateur selon son contexte
    accessible_projects = ContextService.get_user_accessible_projects(request.user)

    # Récupérer tous les projets avec leurs statistiques pour la section projets
    projects_list = accessible_projects.annotate(
        executions_count=Count("executions"), tests_count=Count("tests", distinct=True)
    ).order_by("-created_at")

    # Récupérer tous les projets accessibles pour le header
    all_projects = accessible_projects

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = accessible_projects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    # Vérifier si le projet sélectionné a une configuration CI
    has_ci_configuration = False
    ci_provider = None
    if selected_project:
        try:
            # Importer dynamiquement CIConfiguration pour éviter les imports circulaires
            ci_config = CIConfiguration.objects.filter(project=selected_project).first()
            if ci_config:
                has_ci_configuration = True
                ci_provider = ci_config.get_provider_display()
        except Exception:
            pass

    # Récupérer tous les tags pour la section tags, filtrés par les projets accessibles
    # Note: Dans l'interface d'administration des tags, on affiche TOUS les tags (même exclus)
    # car il s'agit d'une interface d'administration où on doit pouvoir gérer tous les tags
    all_tags = Tag.objects.filter(project__in=accessible_projects).select_related("project").order_by("project__name", "name")

    context = {
        "projects": all_projects,  # Pour le header
        "projects_list": projects_list,  # Pour la section projets
        "selected_project": selected_project,
        "has_ci_configuration": has_ci_configuration,
        "ci_provider": ci_provider,
        "all_tags": all_tags,  # Pour la section tags
    }

    return render(request, "administrations/dashboard.html", context)


def documentation(request):
    """Page principale d'administration avec menu latéral"""
    # Récupérer les projets accessibles par l'utilisateur selon son contexte
    accessible_projects = ContextService.get_user_accessible_projects(request.user)

    # Récupérer tous les projets avec leurs statistiques pour la section projets
    projects_list = accessible_projects.annotate(
        executions_count=Count("executions"), tests_count=Count("tests", distinct=True)
    ).order_by("-created_at")

    # Récupérer tous les projets accessibles pour le header
    all_projects = accessible_projects

    # Récupérer le projet sélectionné depuis la session
    selected_project = None
    if "selected_project_id" in request.session:
        try:
            selected_project = accessible_projects.get(id=request.session["selected_project_id"])
        except Project.DoesNotExist:
            del request.session["selected_project_id"]

    # Vérifier si le projet sélectionné a une configuration CI
    has_ci_configuration = False
    ci_provider = None
    if selected_project:
        try:
            # Importer dynamiquement CIConfiguration pour éviter les imports circulaires
            ci_config = CIConfiguration.objects.filter(project=selected_project).first()
            if ci_config:
                has_ci_configuration = True
                ci_provider = ci_config.get_provider_display()
        except Exception:
            pass

    context = {
        "projects": all_projects,  # Pour le header
        "projects_list": projects_list,  # Pour la section projets
        "selected_project": selected_project,
        "has_ci_configuration": has_ci_configuration,
        "ci_provider": ci_provider,
    }

    return render(request, "documentations/documentation.html", context)


@login_required
def setup_actions(request):
    """
    Page de setup contenant les actions à effectuer pour configurer l'application
    """
    # Vérifier si les groupes sont créés
    groups_exist = Group.objects.filter(name__in=["Admin", "Manager", "Viewer"]).count() == 3

    # Vérifier si le superuser est dans le groupe Admin
    superuser_in_admin = False
    if request.user.is_superuser and groups_exist:
        superuser_in_admin = request.user.groups.filter(name="Admin").exists()

    # Vérifier si au moins un projet existe
    project_exists = Project.objects.exists()

    context = {
        "groups_exist": groups_exist,
        "superuser_in_admin": superuser_in_admin,
        "project_exists": project_exists,
        "is_superuser": request.user.is_superuser,
    }

    return render(request, "core/setup_actions.html", context)


@login_required
def create_groups_and_assign_admin(request):
    """
    Créer les groupes Admin, Manager, Viewer et assigner le superuser au groupe Admin
    """
    if not request.user.is_superuser:
        messages.error(request, "Action réservée au superutilisateur.")
        return redirect("setup_actions")

    if request.method == "POST":
        try:
            # Créer les groupes s'ils n'existent pas
            admin_group, created = Group.objects.get_or_create(name="Admin")
            manager_group, created = Group.objects.get_or_create(name="Manager")
            viewer_group, created = Group.objects.get_or_create(name="Viewer")

            # Assigner le superuser au groupe Admin
            request.user.groups.add(admin_group)

            messages.success(request, "Groupes créés avec succès et superutilisateur ajouté au groupe Admin.")

        except Exception as e:
            messages.error(request, f"Erreur lors de la création des groupes : {str(e)}")

    return redirect("setup_actions")


@login_required
def setup_status(request):
    """
    Vue de débogage pour vérifier l'état de la configuration
    """
    # Vérifier si les groupes sont créés
    groups_exist = Group.objects.filter(name__in=["Admin", "Manager", "Viewer"]).count() == 3
    groups_list = list(Group.objects.filter(name__in=["Admin", "Manager", "Viewer"]).values_list("name", flat=True))

    # Vérifier si le superuser est dans le groupe Admin
    superuser_in_admin = False
    user_groups = []
    if request.user.is_superuser and groups_exist:
        superuser_in_admin = request.user.groups.filter(name="Admin").exists()
        user_groups = list(request.user.groups.values_list("name", flat=True))

    # Vérifier si au moins un projet existe
    project_exists = Project.objects.exists()
    project_count = Project.objects.count()

    setup_complete = groups_exist and superuser_in_admin and project_exists

    return JsonResponse(
        {
            "groups_exist": groups_exist,
            "groups_list": groups_list,
            "superuser_in_admin": superuser_in_admin,
            "user_groups": user_groups,
            "project_exists": project_exists,
            "project_count": project_count,
            "setup_complete": setup_complete,
            "is_superuser": request.user.is_superuser,
            "username": request.user.username,
        }
    )


@login_required
@can_manage_projects
def project_excluded_tags(request, project_id):
    """Vue pour gérer les tags exclus d'un projet"""
    project = get_object_or_404(Project, id=project_id)

    # Récupérer tous les tags du projet
    project_tags = Tag.objects.filter(project=project).order_by("name")

    # Récupérer les tags actuellement exclus
    excluded_tags = project.excluded_tags.all()
    excluded_tag_ids = list(excluded_tags.values_list("id", flat=True))

    if request.method == "POST":
        # Récupérer les IDs des tags à exclure depuis le formulaire
        new_excluded_tag_ids = request.POST.getlist("excluded_tags")
        new_excluded_tag_ids = [int(tag_id) for tag_id in new_excluded_tag_ids if tag_id.isdigit()]

        # Mettre à jour les tags exclus
        project.excluded_tags.set(new_excluded_tag_ids)

        messages.success(request, f"Configuration des tags exclus mise à jour pour le projet '{project.name}'.")
        return redirect("administration_dashboard")

    # Récupérer les projets pour le header
    selected_project, projects, auto_selected = get_selected_project_for_user(request)

    context = {
        "project": project,
        "project_tags": project_tags,
        "excluded_tag_ids": excluded_tag_ids,
        "projects": projects,
        "selected_project": selected_project,
    }

    return render(request, "project/project_excluded_tags.html", context)


def test_404(request):
    """
    Vue de test pour déclencher une erreur 404 - utile pour tester la page d'erreur personnalisée
    """
    raise Http404("Page de test pour l'erreur 404")
