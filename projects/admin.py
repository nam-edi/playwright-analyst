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
    filter_horizontal = ["excluded_tags"]
    inlines = [TagInline, ProjectFeatureInline]

    fieldsets = (
        ("Informations générales", {"fields": ("name", "description", "created_by")}),
        ("Configuration CI", {"fields": ("ci_configuration",), "classes": ["collapse"]}),
        (
            "Configuration d'affichage",
            {
                "fields": ("excluded_tags",),
                "description": "Configurez les tags qui ne seront pas affichés dans le frontend mais resteront en base de données.",
            },
        ),
        ("Métadonnées", {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtrer les tags exclus pour afficher seulement ceux du projet courant"""
        if db_field.name == "excluded_tags":
            # Obtenir l'ID du projet en cours d'édition depuis l'URL
            if request.resolver_match and request.resolver_match.kwargs.get("object_id"):
                try:
                    from testing.models import Tag

                    project_id = request.resolver_match.kwargs["object_id"]
                    kwargs["queryset"] = Tag.objects.filter(project_id=project_id)
                except Exception:
                    pass
        return super().formfield_for_manytomany(db_field, request, **kwargs)

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
