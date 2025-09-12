"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.contrib import admin

from .models import Project, ProjectFeature


class ProjectFeatureInline(admin.TabularInline):
    """Inline pour gérer les features d'un projet"""

    model = ProjectFeature
    extra = 0
    readonly_fields = ["created_at", "updated_at"]
    fields = ["feature_key", "is_enabled", "created_at", "updated_at"]


class TagInline(admin.TabularInline):
    """Inline pour gérer les tags d'un projet"""

    from testing.models import Tag

    model = Tag
    extra = 0
    readonly_fields = ["created_at", "test_count"]
    fields = ["name", "color", "test_count", "created_at"]

    def test_count(self, obj):
        if obj.pk:
            return obj.test_set.count()
        return 0

    test_count.short_description = "Tests"


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
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


@admin.register(ProjectFeature)
class ProjectFeatureAdmin(admin.ModelAdmin):
    list_display = ["project", "feature_key", "is_enabled", "created_at"]
    list_filter = ["feature_key", "is_enabled", "created_at"]
    search_fields = ["project__name"]
    list_editable = ["is_enabled"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("project")
