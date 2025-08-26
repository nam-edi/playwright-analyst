"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Project, Tag, TestExecution, Test, TestResult, CIConfiguration, GitLabConfiguration, GitHubConfiguration
from .widgets import ColorPickerWidget


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


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'ci_provider', 'created_at', 'execution_count']
    list_filter = ['created_at', 'created_by', 'ci_configuration__provider']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def execution_count(self, obj):
        return obj.executions.count()
    execution_count.short_description = 'Exécutions'
    
    def ci_provider(self, obj):
        if obj.ci_configuration:
            return obj.ci_configuration.get_provider_display()
        return "Aucune"
    ci_provider.short_description = 'CI configurée'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    list_display = ['name', 'colored_name', 'color_display', 'test_count']
    search_fields = ['name']
    
    def colored_name(self, obj):
        """Affiche le nom du tag avec sa couleur"""
        return format_html(
            '<span class="admin-tag-color">'
            '<span class="admin-tag-color-dot" style="background-color: {};"></span>'
            '{}'
            '</span>',
            obj.color,
            obj.name
        )
    colored_name.short_description = 'Tag avec couleur'
    
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
    list_display = ['project', 'start_time', 'duration_seconds', 'total_tests', 'success_rate_display', 'git_branch']
    list_filter = ['start_time', 'project', 'git_branch', 'playwright_version']
    search_fields = ['project__name', 'git_commit_hash', 'git_commit_subject']
    readonly_fields = ['created_at', 'total_tests', 'success_rate', 'duration_seconds']
    
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
    
    def duration_seconds(self, obj):
        return f"{obj.duration / 1000:.2f}s"
    duration_seconds.short_description = 'Durée'
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Taux de réussite'


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'file_path', 'line', 'tag_list', 'result_count']
    list_filter = ['tags', 'created_at']
    search_fields = ['title', 'file_path', 'story', 'test_id']
    filter_horizontal = ['tags']
    
    def tag_list(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()[:3]])
    tag_list.short_description = 'Tags'
    
    def result_count(self, obj):
        return obj.results.count()
    result_count.short_description = 'Résultats'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ['test', 'execution_display', 'status', 'duration_seconds', 'has_errors', 'start_time']
    list_filter = ['status', ExecutionListFilter, 'execution__project', 'start_time']
    search_fields = ['test__title', 'execution__project__name']
    readonly_fields = ['duration_seconds', 'has_errors']
    list_per_page = 50  # Augmenter le nombre d'éléments par page
    
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
