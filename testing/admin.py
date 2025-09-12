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
from django.db.models import Count, Q, F, FloatField, Case, When
from django.http import HttpResponse
from datetime import datetime, timedelta
import csv
from .models import Tag, TestExecution, Test, TestResult
from core.widgets import ColorPickerWidget


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


class TagAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour le modèle Tag avec sélecteur de couleur et validation"""
    
    class Meta:
        model = Tag
        fields = '__all__'
        widgets = {
            'color': ColorPickerWidget(attrs={
                'title': 'Choisissez une couleur pour ce tag'
            })
        }


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


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    list_display = ['name', 'project', 'color_display', 'test_count']
    list_filter = ['project', 'created_at']
    search_fields = ['name', 'project__name']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('project')
    
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
    
    def total_tests_display(self, obj):
        return obj.total_tests
    total_tests_display.short_description = 'Tests totaux'
    total_tests_display.admin_order_field = 'expected_tests'  # Approximation pour le tri
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Taux de réussite'


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'file_path', 'line', 'tag_list', 'has_comment', 'result_count']
    list_filter = ['project', 'created_at', TestCommentFilter]
    search_fields = ['title', 'file_path', 'story', 'test_id', 'comment', 'project__name']
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
        tags = obj.tags.all()[:3]
        if tags:
            tag_display = []
            for tag in tags:
                tag_display.append(format_html(
                    '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.8em;">{}</span>',
                    tag.color, tag.name
                ))
            result = ' '.join(tag_display)
            if obj.tags.count() > 3:
                result += f' <span style="color: #6b7280;">+{obj.tags.count() - 3}</span>'
            return format_html(result)
        return "-"
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
