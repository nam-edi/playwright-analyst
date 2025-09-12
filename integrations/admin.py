"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import CIConfiguration, GitHubConfiguration, GitLabConfiguration


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
            self.fields["access_token"].help_text = (
                "Laissez vide pour conserver le token actuel, ou saisissez un nouveau token pour le remplacer."
            )
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
            self.fields["access_token"].help_text = (
                "Laissez vide pour conserver le token actuel, ou saisissez un nouveau token pour le remplacer."
            )
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

    def masked_access_token(self, obj):
        """Affiche le token masqué pour la sécurité"""
        if obj and obj.access_token:
            return format_html('<code style="font-family: monospace; color: #10b981;">{}</code>', obj.masked_access_token)
        return "-"

    masked_access_token.short_description = "Token actuel (masqué)"


@admin.register(CIConfiguration)
class CIConfigurationAdmin(admin.ModelAdmin):
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


@admin.register(GitLabConfiguration)
class GitLabConfigurationAdmin(admin.ModelAdmin):
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


@admin.register(GitHubConfiguration)
class GitHubConfigurationAdmin(admin.ModelAdmin):
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
