"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

import csv
from datetime import datetime, timedelta

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.db.models import Case, Count, F, FloatField, Q, When
from django.forms.widgets import TextInput
from django.http import HttpResponse
from django.utils.html import format_html, mark_safe

from api.models import APIKey
from integrations.models import GitHubConfiguration, GitLabConfiguration

# Les modèles ont été déplacés dans leurs applications respectives
# Import temporaire pour éviter les erreurs
from projects.models import Project, ProjectFeature
from testing.models import Tag, Test, TestExecution, TestResult

# Importer les vues personnalisées pour l'admin
from .models import UserContext
from .widgets import ColorPickerWidget


class EmptyTokenWidget(forms.TextInput):
    """Widget qui force le champ à être vide en modification"""

    def __init__(self, attrs=None):
        default_attrs = {
            "placeholder": "Laissez vide pour conserver le token actuel",
            "style": "border-left: 3px solid #10b981; background-color: #f0fdf4; color: #000000; width: 400px; font-family: monospace;",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def format_value(self, value):
        """Toujours retourner une chaîne vide"""
        return ""

    def value_from_datadict(self, data, files, name):
        """Récupérer la valeur du formulaire"""
        return data.get(name, "")


class GitLabConfigurationForm(forms.ModelForm):
    """Formulaire personnalisé pour GitLabConfiguration avec token masqué"""

    class Meta:
        model = GitLabConfiguration
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:  # En modification
            # Utiliser le widget personnalisé qui force le champ vide
            self.fields["access_token"].widget = EmptyTokenWidget()
            self.fields["access_token"].required = False
            self.fields[
                "access_token"
            ].help_text = "Laissez vide pour conserver le token actuel, ou saisissez un nouveau token pour le remplacer."
            self.fields["access_token"].label = "Nouveau token d'accès (optionnel)"

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Si en modification et token vide, conserver l'ancien
        if self.instance.pk and not self.cleaned_data.get("access_token"):
            old_instance = GitLabConfiguration.objects.get(pk=self.instance.pk)
            instance.access_token = old_instance.access_token
        if commit:
            instance.save()
        return instance


class APIKeyForm(forms.ModelForm):
    """Formulaire personnalisé pour APIKey avec clé masquée et régénération"""

    regenerate_key = forms.BooleanField(
        required=False,
        label="Régénérer la clé API",
        help_text="⚠️ Attention : Cocher cette case générera une nouvelle clé et invalidera l'ancienne définitivement !",
        widget=forms.CheckboxInput(attrs={"style": "transform: scale(1.2); margin-right: 8px;"}),
    )

    class Meta:
        model = APIKey
        exclude = ["key"]  # Exclure complètement le champ key du formulaire

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Gérer la régénération de clé
        if self.cleaned_data.get("regenerate_key"):
            import secrets

            instance.key = secrets.token_urlsafe(32)
        elif self.instance.pk:
            # Conserver l'ancienne clé si pas de régénération
            old_instance = APIKey.objects.get(pk=self.instance.pk)
            instance.key = old_instance.key

        if commit:
            instance.save()
        return instance


class GitHubConfigurationForm(forms.ModelForm):
    """Formulaire personnalisé pour GitHubConfiguration avec token masqué"""

    class Meta:
        model = GitHubConfiguration
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:  # En modification
            # Utiliser le widget personnalisé qui force le champ vide
            self.fields["access_token"].widget = EmptyTokenWidget()
            self.fields["access_token"].required = False
            self.fields[
                "access_token"
            ].help_text = "Laissez vide pour conserver le token actuel, ou saisissez un nouveau token pour le remplacer."
            self.fields["access_token"].label = "Nouveau token d'accès (optionnel)"

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Si en modification et token vide, conserver l'ancien
        if self.instance.pk and not self.cleaned_data.get("access_token"):
            old_instance = GitHubConfiguration.objects.get(pk=self.instance.pk)
            instance.access_token = old_instance.access_token
        if commit:
            instance.save()
        return instance


class TestResultStatusFilter(admin.SimpleListFilter):
    """Filtre de statut avec métriques"""

    title = "Statut avec métriques"
    parameter_name = "status_metrics"

    def lookups(self, request, model_admin):
        # Calculer les statistiques par statut
        status_counts = TestResult.objects.values("status").annotate(count=Count("id")).order_by("-count")

        choices = []
        for item in status_counts:
            status = item["status"]
            count = item["count"]
            display_name = f"{status.title()} ({count})"
            choices.append((status, display_name))

        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class DateRangeFilter(admin.SimpleListFilter):
    """Filtre par période d'exécution"""

    title = "Période d'exécution"
    parameter_name = "date_range"

    def lookups(self, request, model_admin):
        return [
            ("today", "Aujourd'hui"),
            ("week", "Cette semaine"),
            ("month", "Ce mois"),
            ("quarter", "Ce trimestre"),
        ]

    def queryset(self, request, queryset):
        now = datetime.now()

        if self.value() == "today":
            return queryset.filter(start_time__date=now.date())
        elif self.value() == "week":
            week_start = now - timedelta(days=now.weekday())
            return queryset.filter(start_time__gte=week_start)
        elif self.value() == "month":
            return queryset.filter(start_time__year=now.year, start_time__month=now.month)
        elif self.value() == "quarter":
            quarter_start = datetime(now.year, ((now.month - 1) // 3) * 3 + 1, 1)
            return queryset.filter(start_time__gte=quarter_start)

        return queryset


class TestCommentFilter(admin.SimpleListFilter):
    """Filtre pour les tests avec ou sans commentaire"""

    title = "Commentaire"
    parameter_name = "has_comment"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Avec commentaire"),
            ("no", "Sans commentaire"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(comment__isnull=False).exclude(comment="")
        elif self.value() == "no":
            return queryset.filter(Q(comment__isnull=True) | Q(comment=""))
        return queryset


class AdvancedColorPickerWidget(TextInput):
    """Widget de couleur avancé avec palettes prédéfinies et historique"""

    def __init__(self, attrs=None):
        default_attrs = {"class": "advanced-color-picker", "data-color-palette": "true"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        # Couleurs prédéfinies par catégorie
        color_palettes = {
            "status": ["#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#6b7280"],
            "priority": ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#0891b2"],
            "category": ["#7c3aed", "#db2777", "#059669", "#0284c7", "#dc2626"],
        }

        input_html = super().render(name, value, attrs, renderer)

        palette_html = '<div class="color-palette-container">'
        for category, colors in color_palettes.items():
            palette_html += f'<div class="palette-category" data-category="{category}">'
            palette_html += f"<label>{category.title()}</label>"
            palette_html += '<div class="color-grid">'
            for color in colors:
                palette_html += f"""
                    <button type="button" class="color-option"
                            data-color="{color}"
                            style="background-color: {color}"
                            title="{color}">
                    </button>
                """
            palette_html += "</div></div>"
        palette_html += "</div>"

        return mark_safe(input_html + palette_html)

    class Media:
        css = {"all": ("admin/css/advanced_color_picker.css",)}
        js = ("admin/js/advanced_color_picker.js",)


class TestResultInline(admin.TabularInline):
    model = TestResult
    extra = 0
    readonly_fields = ["status", "duration_display", "start_time", "worker_index"]
    fields = ["status", "duration_display", "start_time", "worker_index", "retry"]

    def duration_display(self, obj):
        if obj.duration:
            return f"{obj.duration / 1000:.2f}s"
        return "-"

    duration_display.short_description = "Durée"

    def get_queryset(self, request):
        # Optimiser les requêtes
        return super().get_queryset(request).select_related("execution")


class ExecutionListFilter(admin.SimpleListFilter):
    """Filtre personnalisé pour les exécutions groupées par projet"""

    title = "Exécution"
    parameter_name = "execution"

    def lookups(self, request, model_admin):
        """Retourne les options de filtre groupées par projet"""
        executions = TestExecution.objects.select_related("project").order_by("project__name", "-start_time")

        # Grouper par projet
        projects = {}
        for execution in executions:
            project_name = execution.project.name
            if project_name not in projects:
                projects[project_name] = []

            execution_label = f"{execution.start_time.strftime('%d/%m/%Y %H:%M')}"
            if execution.git_branch:
                execution_label += f" ({execution.git_branch})"

            projects[project_name].append((execution.id, execution_label))

        # Créer les options de filtre
        choices = []
        for project_name, executions in projects.items():
            choices.append((f"project_{project_name}", f"--- {project_name} ---"))
            for exec_id, exec_label in executions[:10]:  # Limiter à 10 par projet
                choices.append((exec_id, f"    {exec_label}"))

        return choices

    def queryset(self, request, queryset):
        """Filtre le queryset selon la sélection"""
        if self.value() and not self.value().startswith("project_"):
            return queryset.filter(execution_id=self.value())
        return queryset


class TagAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour le modèle Tag avec sélecteur de couleur et validation"""

    class Meta:
        model = Tag
        fields = "__all__"
        widgets = {"color": ColorPickerWidget(attrs={"title": "Choisissez une couleur pour ce tag"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Déterminer le projet : soit depuis l'instance existante, soit depuis les données POST
        project_id = None
        if self.instance and self.instance.project_id:
            project_id = self.instance.project_id
        elif "data" in kwargs and kwargs["data"] and "project" in kwargs["data"]:
            # Nouveau tag : récupérer le projet depuis les données POST
            project_id = kwargs["data"].get("project")

        # Si on a un projet, obtenir les couleurs déjà utilisées
        if project_id:
            used_colors = self.get_used_colors_for_project(project_id)
            used_color_values = [color for color, name in used_colors]

            # Passer les couleurs utilisées au widget
            if "color" in self.fields:
                self.fields["color"].widget.attrs["data-used-colors"] = used_color_values

            if used_colors:
                self.fields["color"].help_text = self.build_color_help_text(used_colors)

    def get_used_colors_for_project(self, project_id):
        """Récupère les couleurs déjà utilisées dans le projet"""
        used_colors = (
            Tag.objects.filter(project_id=project_id)
            .exclude(pk=self.instance.pk if self.instance.pk else None)
            .values_list("color", "name")
        )
        return list(used_colors)

    def build_color_help_text(self, used_colors):
        """Construit le texte d'aide avec les couleurs déjà utilisées"""
        if not used_colors:
            return "Toutes les couleurs sont disponibles pour ce projet."

        help_text = "⚠️ <strong>Couleurs déjà utilisées dans ce projet :</strong><br>"
        for color, tag_name in used_colors:
            help_text += f'<span style="display: inline-block; width: 12px; height: 12px; background-color: {color}; border: 1px solid #ccc; margin-right: 5px; vertical-align: middle;"></span>'
            help_text += f'<code>{color}</code> (utilisée par "{tag_name}")<br>'

        return mark_safe(help_text)

    def clean_color(self):
        """Validation personnalisée de la couleur"""
        color = self.cleaned_data.get("color")
        project = self.cleaned_data.get("project")

        if color and project:
            # Vérifier si la couleur est déjà utilisée dans ce projet
            existing_tags = Tag.objects.filter(project=project, color=color).exclude(
                pk=self.instance.pk if self.instance.pk else None
            )

            if existing_tags.exists():
                existing_tag = existing_tags.first()
                raise forms.ValidationError(
                    f'La couleur {color} est déjà utilisée par le tag "{existing_tag.name}" de ce projet. '
                    f"Veuillez choisir une autre couleur."
                )

        return color


class ProjectFeatureInline(admin.TabularInline):
    """Inline pour gérer les features d'un projet"""

    model = ProjectFeature
    extra = 0
    readonly_fields = ["created_at", "updated_at"]
    fields = ["feature_key", "is_enabled", "created_at", "updated_at"]


class TagInline(admin.TabularInline):
    """Inline pour gérer les tags d'un projet"""

    model = Tag
    extra = 0
    readonly_fields = ["created_at", "test_count"]
    fields = ["name", "color", "test_count", "created_at"]

    def test_count(self, obj):
        if obj.pk:
            return obj.test_set.count()
        return 0

    test_count.short_description = "Tests"


# @admin.register(Project)  # Désactivé - modèle déplacé vers projects.admin
class ProjectAdmin_OLD(admin.ModelAdmin):
    list_display = ["name", "created_by", "ci_provider", "created_at", "execution_count", "tags_count", "features_display"]
    list_filter = ["created_at", "created_by", "ci_configuration__provider"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [TagInline, ProjectFeatureInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def execution_count(self, obj):
        return obj.executions.count()

    execution_count.short_description = "Exécutions"

    def tags_count(self, obj):
        return obj.tags.count()

    tags_count.short_description = "Tags"

    def ci_provider(self, obj):
        if obj.ci_configuration:
            return obj.ci_configuration.get_provider_display()
        return "Aucune"

    ci_provider.short_description = "CI configurée"

    def features_display(self, obj):
        """Affiche les features activées pour ce projet"""
        features = obj.features.filter(is_enabled=True)
        if features.exists():
            feature_names = [f.get_feature_key_display() for f in features]
            return ", ".join(feature_names[:2])  # Afficher les 2 premières
        return "Aucune feature"

    features_display.short_description = "Features actives"


# @admin.register(ProjectFeature)  # Désactivé - modèle déplacé vers projects.admin
class ProjectFeatureAdmin_OLD(admin.ModelAdmin):
    list_display = ["project", "feature_key", "is_enabled", "created_at"]
    list_filter = ["feature_key", "is_enabled", "created_at"]
    search_fields = ["project__name"]
    list_editable = ["is_enabled"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("project")


# @admin.register(Tag)  # Désactivé - modèle déplacé vers testing.admin
class TagAdmin_OLD(admin.ModelAdmin):
    form = TagAdminForm
    list_display = ["name", "project", "color_display", "test_count"]
    list_filter = ["project", "created_at"]
    search_fields = ["name", "project__name"]
    readonly_fields = ["created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("project")

    def color_display(self, obj):
        """Affiche un aperçu de la couleur"""
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ddd; border-radius: 3px;"></div>'
            "<code>{}</code>"
            "</div>",
            obj.color,
            obj.color,
        )

    color_display.short_description = "Couleur"

    def test_count(self, obj):
        return obj.test_set.count()

    test_count.short_description = "Tests"

    class Media:
        css = {"all": ("admin/css/color_picker.css",)}
        js = ("admin/js/color_picker.js",)


# @admin.register(TestExecution)  # Désactivé - modèle déplacé vers testing.admin
class TestExecutionAdmin_OLD(admin.ModelAdmin):
    list_display = ["project", "start_time", "duration_seconds", "total_tests_display", "success_rate_display", "git_branch"]
    list_filter = ["start_time", "project", "git_branch", "playwright_version", DateRangeFilter]
    search_fields = ["project__name", "git_commit_hash", "git_commit_subject"]
    readonly_fields = ["created_at", "total_tests_display", "success_rate_display", "duration_seconds"]
    change_list_template = "admin/execution_dashboard.html"

    fieldsets = (
        ("Projet", {"fields": ("project",)}),
        ("Configuration", {"fields": ("config_file", "root_dir", "playwright_version", "workers", "actual_workers")}),
        (
            "Git",
            {
                "fields": (
                    "git_commit_hash",
                    "git_commit_short_hash",
                    "git_branch",
                    "git_commit_subject",
                    "git_author_name",
                    "git_author_email",
                )
            },
        ),
        ("CI/CD", {"fields": ("ci_build_href", "ci_commit_href")}),
        (
            "Statistiques",
            {"fields": ("start_time", "duration", "expected_tests", "skipped_tests", "unexpected_tests", "flaky_tests")},
        ),
        ("Données brutes", {"classes": ("collapse",), "fields": ("raw_json",)}),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Statistiques globales
        executions = TestExecution.objects.all()
        extra_context["total_executions"] = executions.count()

        # Calculer le taux de réussite moyen manuellement
        total_success_rate = 0
        execution_count = 0
        for execution in executions:
            if execution.total_tests > 0:
                total_success_rate += execution.success_rate
                execution_count += 1

        avg_success_rate = total_success_rate / execution_count if execution_count > 0 else 0
        extra_context["avg_success_rate"] = round(avg_success_rate, 1)

        # Graphique des tendances (derniers 30 jours)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_executions = executions.filter(start_time__gte=thirty_days_ago)

        executions_by_date = {}
        for execution in recent_executions:
            date_key = execution.start_time.date()
            if date_key not in executions_by_date:
                executions_by_date[date_key] = {"count": 0, "total_success_rate": 0, "execution_count": 0}

            executions_by_date[date_key]["count"] += 1
            if execution.total_tests > 0:
                executions_by_date[date_key]["total_success_rate"] += execution.success_rate
                executions_by_date[date_key]["execution_count"] += 1

        # Calculer les moyennes
        executions_trend = []
        for date_key, data in executions_by_date.items():
            avg_success = data["total_success_rate"] / data["execution_count"] if data["execution_count"] > 0 else 0
            executions_trend.append(
                {"start_time__date": date_key.isoformat(), "count": data["count"], "avg_success": avg_success}
            )

        executions_trend.sort(key=lambda x: x["start_time__date"])
        extra_context["executions_trend"] = executions_trend

        # Tests les plus problématiques (basé sur les échecs récents)
        problematic_tests = (
            Test.objects.filter(results__execution__start_time__gte=thirty_days_ago)
            .annotate(
                total_runs=Count("results"),
                failed_runs=Count("results", filter=Q(results__status="failed")),
                failure_rate=Case(
                    When(total_runs__gt=0, then=F("failed_runs") * 100.0 / F("total_runs")),
                    default=0,
                    output_field=FloatField(),
                ),
            )
            .filter(total_runs__gte=5)
            .order_by("-failure_rate")[:10]
        )
        extra_context["problematic_tests"] = problematic_tests

        return super().changelist_view(request, extra_context)

    def duration_seconds(self, obj):
        return f"{obj.duration / 1000:.2f}s"

    duration_seconds.short_description = "Durée"

    def total_tests_display(self, obj):
        return obj.total_tests

    total_tests_display.short_description = "Tests totaux"
    total_tests_display.admin_order_field = "expected_tests"  # Approximation pour le tri

    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"

    success_rate_display.short_description = "Taux de réussite"


# @admin.register(Test)  # Désactivé - modèle déplacé vers testing.admin
class TestAdmin_OLD(admin.ModelAdmin):
    list_display = ["title", "project", "file_path", "line", "tag_list", "has_comment", "result_count"]
    list_filter = ["project", "created_at", TestCommentFilter]
    search_fields = ["title", "file_path", "story", "test_id", "comment", "project__name"]
    filter_horizontal = ["tags"]
    inlines = [TestResultInline]

    fieldsets = (
        ("Informations générales", {"fields": ("title", "project", "test_id", "tags")}),
        ("Localisation", {"fields": ("file_path", "line", "column")}),
        (
            "Description",
            {"fields": ("story", "comment"), "description": "Ajoutez des informations supplémentaires sur ce test"},
        ),
        ("Métadonnées", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at"]

    def get_queryset(self, request):
        # Optimiser avec prefetch_related pour éviter les N+1 queries
        return super().get_queryset(request).prefetch_related("tags", "results__execution").select_related("project")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtrer les tags par projet du test en cours d'édition"""
        if db_field.name == "tags":
            # Obtenir l'ID du test en cours d'édition depuis l'URL
            if request.resolver_match and request.resolver_match.kwargs.get("object_id"):
                try:
                    test_id = request.resolver_match.kwargs["object_id"]
                    test = Test.objects.get(pk=test_id)
                    kwargs["queryset"] = Tag.objects.filter(project=test.project)
                except Test.DoesNotExist:
                    pass
            # Pour les nouveaux tests, on ne peut pas filtrer car on ne connaît pas encore le projet
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def tag_list(self, obj):
        tags = obj.tags.all()[:3]
        if tags:
            tag_display = []
            for tag in tags:
                tag_display.append(
                    format_html(
                        '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{}</span>',
                        tag.color,
                        tag.name,
                    )
                )
            result = " ".join(tag_display)
            if obj.tags.count() > 3:
                result += f' <span style="color: #6b7280;">+{obj.tags.count() - 3}</span>'
            return format_html(result)
        return "-"

    tag_list.short_description = "Tags"

    def has_comment(self, obj):
        if obj.comment:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;" title="{}">💬 Oui</span>',
                obj.comment[:100] + "..." if len(obj.comment) > 100 else obj.comment,
            )
        return format_html('<span style="color: #6b7280;">Non</span>')

    has_comment.short_description = "Commentaire"
    has_comment.admin_order_field = "comment"

    def result_count(self, obj):
        return obj.results.count()

    result_count.short_description = "Résultats"


# @admin.register(TestResult)  # Désactivé - modèle déplacé vers testing.admin
class TestResultAdmin_OLD(admin.ModelAdmin):
    list_display = ["test", "execution_display", "status", "duration_seconds", "has_errors", "start_time"]
    list_filter = ["status", ExecutionListFilter, "execution__project", "start_time", TestResultStatusFilter]
    search_fields = ["test__title", "execution__project__name"]
    readonly_fields = ["duration_seconds", "has_errors"]
    list_per_page = 50  # Augmenter le nombre d'éléments par page
    actions = ["mark_as_flaky", "export_failed_tests", "bulk_rerun_tests"]

    @admin.action(description="Marquer comme instables (flaky)")
    def mark_as_flaky(self, request, queryset):
        updated = queryset.update(status="flaky")
        self.message_user(request, f"{updated} test(s) marqué(s) comme instable(s).", messages.SUCCESS)

    @admin.action(description="Exporter les tests échoués")
    def export_failed_tests(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="failed_tests.csv"'

        writer = csv.writer(response)
        writer.writerow(["Test", "Fichier", "Erreur", "Durée", "Exécution"])

        for result in queryset.filter(status="failed"):
            writer.writerow(
                [
                    result.test.title,
                    result.test.file_path,
                    str(result.errors)[:100] if result.errors else "",
                    f"{result.duration / 1000:.2f}s",
                    result.execution.start_time.strftime("%Y-%m-%d %H:%M"),
                ]
            )

        return response

    @admin.action(description="Relancer les tests sélectionnés")
    def bulk_rerun_tests(self, request, queryset):
        test_ids = [result.test.id for result in queryset]
        self.message_user(request, f"Demande de relance pour {len(test_ids)} test(s) enregistrée.", messages.INFO)

    def execution_display(self, obj):
        """Affiche l'exécution de façon plus lisible"""
        return f"{obj.execution.project.name} - {obj.execution.start_time.strftime('%d/%m/%Y %H:%M')}"

    execution_display.short_description = "Exécution"
    execution_display.admin_order_field = "execution__start_time"

    fieldsets = (
        ("Identification", {"fields": ("execution", "test", "project_id", "project_name")}),
        (
            "Exécution",
            {
                "fields": (
                    "status",
                    "expected_status",
                    "timeout",
                    "worker_index",
                    "parallel_index",
                    "retry",
                    "start_time",
                    "duration",
                )
            },
        ),
        (
            "Résultats",
            {"classes": ("collapse",), "fields": ("errors", "stdout", "stderr", "steps", "annotations", "attachments")},
        ),
    )

    def duration_seconds(self, obj):
        return f"{obj.duration / 1000:.2f}s"

    duration_seconds.short_description = "Durée"


class GitLabConfigurationInline(admin.StackedInline):
    """Inline pour la configuration GitLab"""

    model = GitLabConfiguration
    extra = 0
    readonly_fields = ["masked_access_token"]

    def get_fields(self, request, obj=None):
        """Personnalise les champs selon le contexte"""
        if obj and hasattr(obj, "gitlab_config"):
            # Modification : montrer le token masqué en premier
            return ["gitlab_url", "project_id", "masked_access_token", "access_token", "job_name", "artifact_path"]
        else:
            # Création : pas de token masqué encore
            return ["gitlab_url", "project_id", "access_token", "job_name", "artifact_path"]

    def get_formset(self, request, obj=None, **kwargs):
        """Personnalise le formset pour vider le champ access_token en modification"""
        formset = super().get_formset(request, obj, **kwargs)
        if obj and hasattr(obj, "gitlab_config"):
            # En modification, redéfinir complètement le champ access_token
            from django import forms

            formset.form.base_fields["access_token"] = forms.CharField(
                max_length=200,
                required=False,
                initial="",
                widget=forms.TextInput(attrs={"placeholder": "Laissez vide pour conserver"}),
                help_text="Laissez vide pour conserver le token actuel",
                label="Nouveau token (optionnel)",
            )
        return formset

    def masked_access_token(self, obj):
        """Affiche le token masqué pour la sécurité"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; color: #10b981;">{}</code>', obj.masked_access_token)
        return "-"

    masked_access_token.short_description = "Token actuel (masqué)"


class GitHubConfigurationInline(admin.StackedInline):
    """Inline pour la configuration GitHub"""

    model = GitHubConfiguration
    extra = 0
    readonly_fields = ["masked_access_token"]

    def get_fields(self, request, obj=None):
        """Personnalise les champs selon le contexte"""
        if obj and hasattr(obj, "github_config"):
            # Modification : montrer le token masqué en premier
            return ["repository", "masked_access_token", "access_token", "workflow_name", "artifact_name", "json_filename"]
        else:
            # Création : pas de token masqué encore
            return ["repository", "access_token", "workflow_name", "artifact_name", "json_filename"]

    def get_formset(self, request, obj=None, **kwargs):
        """Personnalise le formset pour vider le champ access_token en modification"""
        formset = super().get_formset(request, obj, **kwargs)
        if obj and hasattr(obj, "github_config"):
            # En modification, redéfinir complètement le champ access_token
            from django import forms

            formset.form.base_fields["access_token"] = forms.CharField(
                max_length=200,
                required=False,
                initial="",
                widget=forms.TextInput(attrs={"placeholder": "Laissez vide pour conserver"}),
                help_text="Laissez vide pour conserver le token actuel",
                label="Nouveau token (optionnel)",
            )
        return formset

    def masked_access_token(self, obj):
        """Affiche le token masqué pour la sécurité"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; color: #10b981;">{}</code>', obj.masked_access_token)
        return "-"

    masked_access_token.short_description = "Token actuel (masqué)"


# @admin.register(CIConfiguration)  # Désactivé - modèle déplacé vers integrations.admin
class CIConfigurationAdmin_OLD(admin.ModelAdmin):
    list_display = ["name", "provider", "created_at", "projects_count"]
    list_filter = ["provider", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    def get_inlines(self, request, obj):
        """Retourne les inlines selon le provider"""
        if obj and obj.provider == "gitlab":
            return [GitLabConfigurationInline]
        elif obj and obj.provider == "github":
            return [GitHubConfigurationInline]
        return []

    def projects_count(self, obj):
        return obj.project_set.count()

    projects_count.short_description = "Projets utilisant cette config"


# @admin.register(GitLabConfiguration)  # Désactivé - modèle déplacé vers integrations.admin
class GitLabConfigurationAdmin_OLD(admin.ModelAdmin):
    form = GitLabConfigurationForm
    list_display = ["ci_config", "gitlab_url", "project_id", "job_name", "masked_token_display"]
    search_fields = ["ci_config__name", "project_id", "job_name"]
    readonly_fields = ["masked_access_token"]

    fieldsets = (
        ("Configuration CI", {"fields": ("ci_config",)}),
        ("Connexion GitLab", {"fields": ("gitlab_url", "project_id")}),
        (
            "Authentification",
            {
                "fields": ("masked_access_token", "access_token"),
                "description": "Le token actuel est masqué ci-dessus. Laissez le champ ci-dessous vide pour conserver le token existant, ou saisissez un nouveau token pour le remplacer.",
            },
        ),
        ("Configuration des artifacts", {"fields": ("job_name", "artifact_path")}),
    )

    def get_fieldsets(self, request, obj=None):
        """Retourne les fieldsets seulement en modification"""
        if obj:
            return self.fieldsets
        else:
            return (
                (
                    "Configuration",
                    {"fields": ("ci_config", "gitlab_url", "project_id", "access_token", "job_name", "artifact_path")},
                ),
            )

    def masked_access_token(self, obj):
        """Affiche le token masqué pour la sécurité"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; color: #10b981;">{}</code>', obj.masked_access_token)
        return "-"

    masked_access_token.short_description = "Token actuel (masqué)"

    def masked_token_display(self, obj):
        """Affichage du token masqué dans la liste"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; font-size: 0.9em;">{}</code>', obj.masked_access_token)
        return format_html('<span style="color: #ef4444;">Non configuré</span>')

    masked_token_display.short_description = "Token"


# @admin.register(GitHubConfiguration)  # Désactivé - modèle déplacé vers integrations.admin
class GitHubConfigurationAdmin_OLD(admin.ModelAdmin):
    form = GitHubConfigurationForm
    list_display = ["ci_config", "repository", "workflow_name", "artifact_name", "masked_token_display"]
    search_fields = ["ci_config__name", "repository", "workflow_name"]
    readonly_fields = ["masked_access_token"]

    fieldsets = (
        ("Configuration CI", {"fields": ("ci_config",)}),
        ("Repository GitHub", {"fields": ("repository",)}),
        (
            "Authentification",
            {
                "fields": ("masked_access_token", "access_token"),
                "description": "Le token actuel est masqué ci-dessus. Laissez le champ ci-dessous vide pour conserver le token existant, ou saisissez un nouveau token pour le remplacer.",
            },
        ),
        ("Configuration du workflow", {"fields": ("workflow_name", "artifact_name", "json_filename")}),
    )

    def get_fieldsets(self, request, obj=None):
        """Retourne les fieldsets seulement en modification"""
        if obj:
            return self.fieldsets
        else:
            return (
                (
                    "Configuration",
                    {"fields": ("ci_config", "repository", "access_token", "workflow_name", "artifact_name", "json_filename")},
                ),
            )

    def masked_access_token(self, obj):
        """Affiche le token masqué pour la sécurité"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; color: #10b981;">{}</code>', obj.masked_access_token)
        return "-"

    masked_access_token.short_description = "Token actuel (masqué)"

    def masked_token_display(self, obj):
        """Affichage du token masqué dans la liste"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; font-size: 0.9em;">{}</code>', obj.masked_access_token)
        return format_html('<span style="color: #ef4444;">Non configuré</span>')

    masked_token_display.short_description = "Token"


# @admin.register(APIKey)  # Désactivé - modèle déplacé vers api.admin
class APIKeyAdmin_OLD(admin.ModelAdmin):
    form = APIKeyForm
    list_display = [
        "name",
        "user",
        "masked_key",
        "projects_count",
        "permissions_display",
        "is_active",
        "last_used",
        "expires_at",
    ]
    list_filter = ["is_active", "can_upload", "can_read", "created_at", "expires_at"]
    search_fields = ["name", "user__username", "user__email"]
    readonly_fields = ["created_at", "last_used", "masked_key"]
    exclude_in_creation = ["key", "masked_key", "regenerate_key"]
    filter_horizontal = ["projects"]

    fieldsets = (
        ("Informations générales", {"fields": ("name", "user", "masked_key")}),
        (
            "Régénération",
            {
                "fields": ("regenerate_key",),
                "description": "Cochez cette case pour générer une nouvelle clé API. L'ancienne clé sera immédiatement invalidée.",
                "classes": ("wide",),
            },
        ),
        (
            "Permissions",
            {
                "fields": ("can_upload", "can_read", "projects"),
                "description": "Si aucun projet n'est sélectionné, la clé aura accès à tous les projets.",
            },
        ),
        ("État", {"fields": ("is_active", "expires_at")}),
        ("Métadonnées", {"fields": ("created_at", "last_used"), "classes": ("collapse",)}),
    )

    def get_fieldsets(self, request, obj=None):
        """Personnalise les fieldsets selon le contexte"""
        if obj:  # Modification
            return self.fieldsets
        else:  # Création
            return (
                ("Informations générales", {"fields": ("name", "user")}),
                (
                    "Permissions",
                    {
                        "fields": ("can_upload", "can_read", "projects"),
                        "description": "Si aucun projet n'est sélectionné, la clé aura accès à tous les projets.",
                    },
                ),
                ("État", {"fields": ("is_active", "expires_at")}),
            )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user").prefetch_related("projects")

    def save_model(self, request, obj, form, change):
        """Gérer la création et régénération de clés"""
        if not change:  # Nouveau modèle
            obj.user = obj.user or request.user

        # Vérifier si une régénération est demandée
        regenerate_requested = form.cleaned_data.get("regenerate_key", False)

        super().save_model(request, obj, form, change)

        # Messages informatifs
        if not change:
            messages.success(
                request,
                f"🎉 Clé API créée avec succès ! Voici la clé complète (notez-la, elle ne sera plus affichée) : {obj.key}",
            )
        elif regenerate_requested:
            messages.warning(
                request,
                f"🔄 Clé API régénérée avec succès ! Nouvelle clé : {obj.key} (⚠️ L'ancienne clé est maintenant invalidée)",
            )

    def projects_count(self, obj):
        """Affiche le nombre de projets autorisés"""
        count = obj.projects.count()
        if count == 0:
            return format_html('<span style="color: #10b981;">Tous les projets</span>')
        return format_html('<span title="Projets spécifiques">{} projet(s)</span>', count)

    projects_count.short_description = "Projets autorisés"

    def permissions_display(self, obj):
        """Affiche les permissions de façon lisible"""
        perms = []
        if obj.can_read:
            perms.append("📖 Lecture")
        if obj.can_upload:
            perms.append("📤 Upload")

        if not perms:
            return format_html('<span style="color: #ef4444;">Aucune permission</span>')

        return format_html('<span title="{}">{}</span>', ", ".join(perms), " + ".join(perms))

    permissions_display.short_description = "Permissions"

    def masked_key(self, obj):
        """Affiche la clé masquée"""
        if obj.key:
            return format_html('<code style="font-family: monospace;">{}</code>', obj.masked_key)
        return "-"

    masked_key.short_description = "Clé (masquée)"

    actions = ["deactivate_keys", "extend_expiry"]

    @admin.action(description="Désactiver les clés sélectionnées")
    def deactivate_keys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} clé(s) API désactivée(s).", messages.SUCCESS)

    @admin.action(description="Prolonger l'expiration de 30 jours")
    def extend_expiry(self, request, queryset):
        from django.utils import timezone

        new_expiry = timezone.now() + timedelta(days=30)
        updated = queryset.update(expires_at=new_expiry)
        self.message_user(
            request,
            f'Expiration prolongée pour {updated} clé(s) API (nouveau délai : {new_expiry.strftime("%d/%m/%Y")}).',
            messages.SUCCESS,
        )


# Personnalisation de l'admin pour injecter des données dans la page d'accueil
class PWAnalystAdminSite(admin.AdminSite):
    """Site admin personnalisé avec des données supplémentaires pour la page d'accueil"""

    def index(self, request, extra_context=None):
        """Vue personnalisée pour la page d'accueil avec métriques"""
        extra_context = extra_context or {}

        # Calculer les métriques pour la page d'accueil
        total_tests = Test.objects.count()
        total_test_results = TestResult.objects.count()
        active_projects = Project.objects.filter(executions__isnull=False).distinct().count()

        # Calculer le taux de réussite global
        if total_test_results > 0:
            passed_tests = TestResult.objects.filter(status="passed").count()
            success_rate = round((passed_tests / total_test_results) * 100, 1)
        else:
            success_rate = 0

        # Tests en échec récents
        failed_tests = TestResult.objects.filter(status="failed").count()

        # Ajouter les données au contexte
        extra_context.update(
            {
                "total_tests": total_tests,
                "success_rate": success_rate,
                "failed_tests": failed_tests,
                "active_projects": active_projects,
            }
        )

        return super().index(request, extra_context)


class UserContextAdmin(admin.ModelAdmin):
    """Administration des contextes utilisateurs"""

    list_display = ("user", "get_user_groups", "get_projects_count", "created_at")
    list_filter = ("created_at", "user__groups")
    search_fields = ("user__username", "user__first_name", "user__last_name")
    filter_horizontal = ("projects",)

    def get_user_groups(self, obj):
        groups = obj.user.groups.all()
        if groups:
            return ", ".join([group.name for group in groups])
        return "Aucun groupe"

    get_user_groups.short_description = "Groupes"

    def get_projects_count(self, obj):
        count = obj.get_projects_count()
        if count == 0:
            return "Tous les projets"
        return f"{count} projet{'s' if count > 1 else ''}"

    get_projects_count.short_description = "Projets accessibles"

    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related("user").prefetch_related("user__groups", "projects")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filtrer les utilisateurs selon leurs groupes"""
        if db_field.name == "user":
            # Seuls les utilisateurs Manager et Viewer peuvent avoir un contexte
            kwargs["queryset"] = User.objects.filter(groups__name__in=["Manager", "Viewer"]).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Enregistrer le modèle
admin.site.register(UserContext, UserContextAdmin)


# Remplacer le site admin par défaut si nécessaire
# Mais gardons admin.site pour la compatibilité
def get_admin_metrics():
    """Fonction utilitaire pour obtenir les métriques admin"""
    return {
        "total_tests": Test.objects.count(),
        "total_test_results": TestResult.objects.count(),
        "active_projects": Project.objects.filter(executions__isnull=False).distinct().count(),
        "failed_tests": TestResult.objects.filter(status="failed").count(),
    }
