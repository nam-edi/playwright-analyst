"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.db import models


class CIConfiguration(models.Model):
    """Configuration CI abstraite"""
    CI_PROVIDER_CHOICES = [
        ('gitlab', 'GitLab'),
        ('github', 'GitHub'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Nom de la configuration")
    provider = models.CharField(max_length=20, choices=CI_PROVIDER_CHOICES, verbose_name="Fournisseur CI")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    class Meta:
        verbose_name = "Configuration CI"
        verbose_name_plural = "Configurations CI"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"


class GitLabConfiguration(models.Model):
    """Configuration pour GitLab CI"""
    ci_config = models.OneToOneField(CIConfiguration, on_delete=models.CASCADE, related_name='gitlab_config')
    
    # Authentification
    gitlab_url = models.URLField(verbose_name="URL GitLab", help_text="Ex: https://gitlab.com")
    project_id = models.CharField(max_length=100, verbose_name="ID du projet GitLab")
    access_token = models.CharField(max_length=200, verbose_name="Token d'accès", help_text="Token avec permissions API. ⚠️ Sera stocké de manière sécurisée et masqué dans l'interface.")
    
    # Configuration des artifacts
    job_name = models.CharField(max_length=200, verbose_name="Nom du job", help_text="Nom du job contenant les artifacts")
    artifact_path = models.CharField(max_length=500, verbose_name="Chemin vers le JSON", help_text="Chemin du fichier JSON dans les artifacts")
    
    class Meta:
        verbose_name = "Configuration GitLab"
        verbose_name_plural = "Configurations GitLab"
    
    def __str__(self):
        return f"GitLab - {self.project_id}"
    
    @property
    def masked_access_token(self):
        """Retourne une version masquée du token pour l'affichage"""
        if not self.access_token:
            return ""
        if len(self.access_token) <= 8:
            return '*' * len(self.access_token)
        return self.access_token[:4] + '*' * (len(self.access_token) - 8) + self.access_token[-4:]


class GitHubConfiguration(models.Model):
    """Configuration pour GitHub Actions"""
    ci_config = models.OneToOneField(CIConfiguration, on_delete=models.CASCADE, related_name='github_config')
    
    # Authentification
    repository = models.CharField(max_length=200, verbose_name="Repository", help_text="Format: owner/repo")
    access_token = models.CharField(max_length=200, verbose_name="Token d'accès", help_text="GitHub Personal Access Token. ⚠️ Sera stocké de manière sécurisée et masqué dans l'interface.")
    
    # Configuration des artifacts
    workflow_name = models.CharField(max_length=200, verbose_name="Nom du workflow", help_text="Nom du workflow GitHub Actions")
    artifact_name = models.CharField(max_length=200, verbose_name="Nom de l'artifact", help_text="Nom de l'artifact contenant les résultats")
    json_filename = models.CharField(max_length=200, verbose_name="Nom du fichier JSON", help_text="Nom du fichier JSON dans l'artifact")
    
    class Meta:
        verbose_name = "Configuration GitHub"
        verbose_name_plural = "Configurations GitHub"
    
    def __str__(self):
        return f"GitHub - {self.repository}"
    
    @property
    def masked_access_token(self):
        """Retourne une version masquée du token pour l'affichage"""
        if not self.access_token:
            return ""
        if len(self.access_token) <= 8:
            return '*' * len(self.access_token)
        return self.access_token[:4] + '*' * (len(self.access_token) - 8) + self.access_token[-4:]
