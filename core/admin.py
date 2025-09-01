"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django import forms
from django.contrib import messages
from django.db.models import Count, Avg, Case, When, FloatField, Q, F
from django.http import HttpResponse
from django.forms.widgets import TextInput
from datetime import datetime, timedelta
import csv
from .models import Project, Tag, TestExecution, Test, TestResult, CIConfiguration, GitLabConfiguration, GitHubConfiguration, ProjectFeature
from .widgets import ColorPickerWidget


class TestResultStatusFilter(admin.SimpleListFilter):
    """Filtre de statut avec métriques"""
    title = 'Statut avec métriques'
    parameter_name = 'status_metrics'
    
    def lookups(self, request, model_admin):
        # Calculer les statistiques par statut
        status_counts = TestResult.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        choices = []
        for item in status_counts:
            status = item['status']
            count = item['count']
            display_name = f"{status.title()} ({count})"
            choices.append((status, display_name))
        
        return choices
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class DateRangeFilter(admin.SimpleListFilter):
    """Filtre par période d'exécution"""
    title = 'Période d\'exécution'
    parameter_name = 'date_range'
    
    def lookups(self, request, model_admin):
        return [
            ('today', 'Aujourd\'hui'),
            ('week', 'Cette semaine'),
            ('month', 'Ce mois'),
            ('quarter', 'Ce trimestre'),
        ]
    
    def queryset(self, request, queryset):
        now = datetime.now()
        
        if self.value() == 'today':
            return queryset.filter(start_time__date=now.date())
        elif self.value() == 'week':
            week_start = now - timedelta(days=now.weekday())
            return queryset.filter(start_time__gte=week_start)
        elif self.value() == 'month':
            return queryset.filter(
                start_time__year=now.year,
                start_time__month=now.month
            )
        elif self.value() == 'quarter':
            quarter_start = datetime(now.year, ((now.month-1)//3)*3+1, 1)
            return queryset.filter(start_time__gte=quarter_start)
        
        return queryset


class TestCommentFilter(admin.SimpleListFilter):
    """Filtre pour les tests avec ou sans commentaire"""
    title = 'Commentaire'
    parameter_name = 'has_comment'
    
    def lookups(self, request, model_admin):
        return [
            ('yes', 'Avec commentaire'),
            ('no', 'Sans commentaire'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(comment__isnull=False).exclude(comment='')
        elif self.value() == 'no':
            return queryset.filter(Q(comment__isnull=True) | Q(comment=''))
        return queryset


class AdvancedColorPickerWidget(TextInput):
    """Widget de couleur avancé avec palettes prédéfinies et historique"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'advanced-color-picker',
            'data-color-palette': 'true'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        # Couleurs prédéfinies par catégorie
        color_palettes = {
            'status': ['#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#6b7280'],
            'priority': ['#dc2626', '#ea580c', '#ca8a04', '#16a34a', '#0891b2'],
            'category': ['#7c3aed', '#db2777', '#059669', '#0284c7', '#dc2626']
        }
        
        input_html = super().render(name, value, attrs, renderer)
        
        palette_html = '<div class="color-palette-container">'
        for category, colors in color_palettes.items():
            palette_html += f'<div class="palette-category" data-category="{category}">'
            palette_html += f'<label>{category.title()}</label>'
            palette_html += '<div class="color-grid">'
            for color in colors:
                palette_html += f'''
                    <button type="button" class="color-option" 
                            data-color="{color}" 
                            style="background-color: {color}"
                            title="{color}">
                    </button>
                '''
            palette_html += '</div></div>'
        palette_html += '</div>'
        
        return mark_safe(input_html + palette_html)
    
    class Media:
        css = {
            'all': ('admin/css/advanced_color_picker.css',)
        }
        js = ('admin/js/advanced_color_picker.js',)


class TestResultInline(admin.TabularInline):
    model = TestResult
    extra = 0
    readonly_fields = ['status', 'duration_display', 'start_time', 'worker_index']
    fields = ['status', 'duration_display', 'start_time', 'worker_index', 'retry']
    
    def duration_display(self, obj):
        if obj.duration:
            return f"{obj.duration / 1000:.2f}s"
        return "-"
    duration_display.short_description = 'Durée'
    
    def get_queryset(self, request):
        # Optimiser les requêtes
        return super().get_queryset(request).select_related('execution')


class ExecutionListFilter(admin.SimpleListFilter):
    """Filtre personnalisé pour les exécutions groupées par projet"""
    title = 'Exécution'
    parameter_name = 'execution'

    def lookups(self, request, model_admin):
        """Retourne les options de filtre groupées par projet"""
        executions = TestExecution.objects.select_related('project').order_by('project__name', '-start_time')
        
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
        if self.value() and not self.value().startswith('project_'):
            return queryset.filter(execution_id=self.value())
        return queryset


class TagAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour le modèle Tag avec sélecteur de couleur"""
    
    class Meta:
        model = Tag
        fields = '__all__'
        widgets = {
            'color': ColorPickerWidget(attrs={
                'title': 'Choisissez une couleur pour ce tag'
            })
        }


class ProjectFeatureInline(admin.TabularInline):
    """Inline pour gérer les features d'un projet"""
    model = ProjectFeature
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['feature_key', 'is_enabled', 'created_at', 'updated_at']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'ci_provider', 'created_at', 'execution_count', 'features_display']
    list_filter = ['created_at', 'created_by', 'ci_configuration__provider']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProjectFeatureInline]
    
    def execution_count(self, obj):
        return obj.executions.count()
    execution_count.short_description = 'Exécutions'
    
    def ci_provider(self, obj):
        if obj.ci_configuration:
            return obj.ci_configuration.get_provider_display()
        return "Aucune"
    ci_provider.short_description = 'CI configurée'
    
    def features_display(self, obj):
        """Affiche les features activées pour ce projet"""
        features = obj.features.filter(is_enabled=True)
        if features.exists():
            feature_names = [f.get_feature_key_display() for f in features]
            return ", ".join(feature_names[:2])  # Afficher les 2 premières
        return "Aucune feature"
    features_display.short_description = 'Features actives'


@admin.register(ProjectFeature)
class ProjectFeatureAdmin(admin.ModelAdmin):
    list_display = ['project', 'feature_key', 'is_enabled', 'created_at']
    list_filter = ['feature_key', 'is_enabled', 'created_at']
    search_fields = ['project__name']
    list_editable = ['is_enabled']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    list_display = ['name', 'color_display', 'test_count']
    search_fields = ['name']
    
    def color_display(self, obj):
        """Affiche un aperçu de la couleur"""
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ddd; border-radius: 3px;"></div>'
            '<code>{}</code>'
            '</div>',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Couleur'
    
    def test_count(self, obj):
        return obj.test_set.count()
    test_count.short_description = 'Tests'
    
    class Media:
        css = {
            'all': ('admin/css/color_picker.css',)
        }
        js = ('admin/js/color_picker.js',)


@admin.register(TestExecution)
class TestExecutionAdmin(admin.ModelAdmin):
    list_display = ['project', 'start_time', 'duration_seconds', 'total_tests_display', 'success_rate_display', 'git_branch']
    list_filter = ['start_time', 'project', 'git_branch', 'playwright_version', DateRangeFilter]
    search_fields = ['project__name', 'git_commit_hash', 'git_commit_subject']
    readonly_fields = ['created_at', 'total_tests_display', 'success_rate_display', 'duration_seconds']
    change_list_template = 'admin/execution_dashboard.html'
    
    fieldsets = (
        ('Projet', {
            'fields': ('project',)
        }),
        ('Configuration', {
            'fields': ('config_file', 'root_dir', 'playwright_version', 'workers', 'actual_workers')
        }),
        ('Git', {
            'fields': ('git_commit_hash', 'git_commit_short_hash', 'git_branch', 'git_commit_subject', 'git_author_name', 'git_author_email')
        }),
        ('CI/CD', {
            'fields': ('ci_build_href', 'ci_commit_href')
        }),
        ('Statistiques', {
            'fields': ('start_time', 'duration', 'expected_tests', 'skipped_tests', 'unexpected_tests', 'flaky_tests')
        }),
        ('Données brutes', {
            'classes': ('collapse',),
            'fields': ('raw_json',)
        })
    )
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Statistiques globales
        executions = TestExecution.objects.all()
        extra_context['total_executions'] = executions.count()
        
        # Calculer le taux de réussite moyen manuellement
        total_success_rate = 0
        execution_count = 0
        for execution in executions:
            if execution.total_tests > 0:
                total_success_rate += execution.success_rate
                execution_count += 1
        
        avg_success_rate = total_success_rate / execution_count if execution_count > 0 else 0
        extra_context['avg_success_rate'] = round(avg_success_rate, 1)
        
        # Graphique des tendances (derniers 30 jours)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_executions = executions.filter(start_time__gte=thirty_days_ago)
        
        executions_by_date = {}
        for execution in recent_executions:
            date_key = execution.start_time.date()
            if date_key not in executions_by_date:
                executions_by_date[date_key] = {
                    'count': 0,
                    'total_success_rate': 0,
                    'execution_count': 0
                }
            
            executions_by_date[date_key]['count'] += 1
            if execution.total_tests > 0:
                executions_by_date[date_key]['total_success_rate'] += execution.success_rate
                executions_by_date[date_key]['execution_count'] += 1
        
        # Calculer les moyennes
        executions_trend = []
        for date_key, data in executions_by_date.items():
            avg_success = data['total_success_rate'] / data['execution_count'] if data['execution_count'] > 0 else 0
            executions_trend.append({
                'start_time__date': date_key.isoformat(),
                'count': data['count'],
                'avg_success': avg_success
            })
        
        executions_trend.sort(key=lambda x: x['start_time__date'])
        extra_context['executions_trend'] = executions_trend
        
        # Tests les plus problématiques (basé sur les échecs récents)
        problematic_tests = Test.objects.filter(
            results__execution__start_time__gte=thirty_days_ago
        ).annotate(
            total_runs=Count('results'),
            failed_runs=Count('results', filter=Q(results__status='failed')),
            failure_rate=Case(
                When(total_runs__gt=0, then=F('failed_runs') * 100.0 / F('total_runs')),
                default=0,
                output_field=FloatField()
            )
        ).filter(total_runs__gte=5).order_by('-failure_rate')[:10]
        extra_context['problematic_tests'] = problematic_tests
        
        return super().changelist_view(request, extra_context)
    
    def duration_seconds(self, obj):
        return f"{obj.duration / 1000:.2f}s"
    duration_seconds.short_description = 'Durée'
    
    def total_tests_display(self, obj):
        return obj.total_tests
    total_tests_display.short_description = 'Tests totaux'
    total_tests_display.admin_order_field = 'expected_tests'  # Approximation pour le tri
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Taux de réussite'


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_path', 'line', 'tag_list', 'has_comment', 'result_count']
    list_filter = ['tags', 'created_at', TestCommentFilter]
    search_fields = ['title', 'file_path', 'story', 'test_id', 'comment']
    filter_horizontal = ['tags']
    inlines = [TestResultInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'project', 'test_id', 'tags')
        }),
        ('Localisation', {
            'fields': ('file_path', 'line', 'column')
        }),
        ('Description', {
            'fields': ('story', 'comment'),
            'description': 'Ajoutez des informations supplémentaires sur ce test'
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        # Optimiser avec prefetch_related pour éviter les N+1 queries
        return super().get_queryset(request).prefetch_related(
            'tags', 'results__execution'
        ).select_related('project')
    
    def tag_list(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()[:3]])
    tag_list.short_description = 'Tags'
    
    def has_comment(self, obj):
        if obj.comment:
            return format_html(
                '<span style="color: #10b981; font-weight: bold;" title="{}">💬 Oui</span>',
                obj.comment[:100] + '...' if len(obj.comment) > 100 else obj.comment
            )
        return format_html('<span style="color: #6b7280;">Non</span>')
    has_comment.short_description = 'Commentaire'
    has_comment.admin_order_field = 'comment'
    
    def result_count(self, obj):
        return obj.results.count()
    result_count.short_description = 'Résultats'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['test', 'execution_display', 'status', 'duration_seconds', 'has_errors', 'start_time']
    list_filter = ['status', ExecutionListFilter, 'execution__project', 'start_time', TestResultStatusFilter]
    search_fields = ['test__title', 'execution__project__name']
    readonly_fields = ['duration_seconds', 'has_errors']
    list_per_page = 50  # Augmenter le nombre d'éléments par page
    actions = ['mark_as_flaky', 'export_failed_tests', 'bulk_rerun_tests']
    
    @admin.action(description='Marquer comme instables (flaky)')
    def mark_as_flaky(self, request, queryset):
        updated = queryset.update(status='flaky')
        self.message_user(
            request,
            f'{updated} test(s) marqué(s) comme instable(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='Exporter les tests échoués')
    def export_failed_tests(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="failed_tests.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Test', 'Fichier', 'Erreur', 'Durée', 'Exécution'])
        
        for result in queryset.filter(status='failed'):
            writer.writerow([
                result.test.title,
                result.test.file_path,
                str(result.errors)[:100] if result.errors else '',
                f"{result.duration/1000:.2f}s",
                result.execution.start_time.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    
    @admin.action(description='Relancer les tests sélectionnés')
    def bulk_rerun_tests(self, request, queryset):
        test_ids = [result.test.id for result in queryset]
        self.message_user(
            request,
            f'Demande de relance pour {len(test_ids)} test(s) enregistrée.',
            messages.INFO
        )
    
    def execution_display(self, obj):
        """Affiche l'exécution de façon plus lisible"""
        return f"{obj.execution.project.name} - {obj.execution.start_time.strftime('%d/%m/%Y %H:%M')}"
    execution_display.short_description = 'Exécution'
    execution_display.admin_order_field = 'execution__start_time'
    
    fieldsets = (
        ('Identification', {
            'fields': ('execution', 'test', 'project_id', 'project_name')
        }),
        ('Exécution', {
            'fields': ('status', 'expected_status', 'timeout', 'worker_index', 'parallel_index', 'retry', 'start_time', 'duration')
        }),
        ('Résultats', {
            'classes': ('collapse',),
            'fields': ('errors', 'stdout', 'stderr', 'steps', 'annotations', 'attachments')
        })
    )
    
    def duration_seconds(self, obj):
        return f"{obj.duration / 1000:.2f}s"
    duration_seconds.short_description = 'Durée'


class GitLabConfigurationInline(admin.StackedInline):
    """Inline pour la configuration GitLab"""
    model = GitLabConfiguration
    extra = 0
    fields = ['gitlab_url', 'project_id', 'access_token', 'job_name', 'artifact_path']


class GitHubConfigurationInline(admin.StackedInline):
    """Inline pour la configuration GitHub"""
    model = GitHubConfiguration
    extra = 0
    fields = ['repository', 'access_token', 'workflow_name', 'artifact_name', 'json_filename']


@admin.register(CIConfiguration)
class CIConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'created_at', 'projects_count']
    list_filter = ['provider', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_inlines(self, request, obj):
        """Retourne les inlines selon le provider"""
        if obj and obj.provider == 'gitlab':
            return [GitLabConfigurationInline]
        elif obj and obj.provider == 'github':
            return [GitHubConfigurationInline]
        return []
    
    def projects_count(self, obj):
        return obj.project_set.count()
    projects_count.short_description = 'Projets utilisant cette config'


@admin.register(GitLabConfiguration)
class GitLabConfigurationAdmin(admin.ModelAdmin):
    list_display = ['ci_config', 'gitlab_url', 'project_id', 'job_name']
    search_fields = ['ci_config__name', 'project_id', 'job_name']
    fields = ['ci_config', 'gitlab_url', 'project_id', 'access_token', 'job_name', 'artifact_path']


@admin.register(GitHubConfiguration)
class GitHubConfigurationAdmin(admin.ModelAdmin):
    list_display = ['ci_config', 'repository', 'workflow_name', 'artifact_name']
    search_fields = ['ci_config__name', 'repository', 'workflow_name']
    fields = ['ci_config', 'repository', 'access_token', 'workflow_name', 'artifact_name', 'json_filename']


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
            passed_tests = TestResult.objects.filter(status='passed').count()
            success_rate = round((passed_tests / total_test_results) * 100, 1)
        else:
            success_rate = 0
        
        # Tests en échec récents
        failed_tests = TestResult.objects.filter(status='failed').count()
        
        # Ajouter les données au contexte
        extra_context.update({
            'total_tests': total_tests,
            'success_rate': success_rate,
            'failed_tests': failed_tests,
            'active_projects': active_projects,
        })
        
        return super().index(request, extra_context)

# Remplacer le site admin par défaut si nécessaire
# Mais gardons admin.site pour la compatibilité
def get_admin_metrics():
    """Fonction utilitaire pour obtenir les métriques admin"""
    return {
        'total_tests': Test.objects.count(),
        'total_test_results': TestResult.objects.count(),
        'active_projects': Project.objects.filter(executions__isnull=False).distinct().count(),
        'failed_tests': TestResult.objects.filter(status='failed').count(),
    }
