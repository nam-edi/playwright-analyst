"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.db import models
from django.contrib.auth.models import User
import json


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
    access_token = models.CharField(max_length=200, verbose_name="Token d'accès", help_text="Token avec permissions API")
    
    # Configuration des artifacts
    job_name = models.CharField(max_length=200, verbose_name="Nom du job", help_text="Nom du job contenant les artifacts")
    artifact_path = models.CharField(max_length=500, verbose_name="Chemin vers le JSON", help_text="Chemin du fichier JSON dans les artifacts")
    
    class Meta:
        verbose_name = "Configuration GitLab"
        verbose_name_plural = "Configurations GitLab"
    
    def __str__(self):
        return f"GitLab - {self.project_id}"


class GitHubConfiguration(models.Model):
    """Configuration pour GitHub Actions"""
    ci_config = models.OneToOneField(CIConfiguration, on_delete=models.CASCADE, related_name='github_config')
    
    # Authentification
    repository = models.CharField(max_length=200, verbose_name="Repository", help_text="Format: owner/repo")
    access_token = models.CharField(max_length=200, verbose_name="Token d'accès", help_text="GitHub Personal Access Token")
    
    # Configuration des artifacts
    workflow_name = models.CharField(max_length=200, verbose_name="Nom du workflow", help_text="Nom du workflow GitHub Actions")
    artifact_name = models.CharField(max_length=200, verbose_name="Nom de l'artifact", help_text="Nom de l'artifact contenant les résultats")
    json_filename = models.CharField(max_length=200, verbose_name="Nom du fichier JSON", help_text="Nom du fichier JSON dans l'artifact")
    
    class Meta:
        verbose_name = "Configuration GitHub"
        verbose_name_plural = "Configurations GitHub"
    
    def __str__(self):
        return f"GitHub - {self.repository}"


class Project(models.Model):
    """Projet contenant plusieurs exécutions de tests"""
    name = models.CharField(max_length=200, verbose_name="Nom du projet")
    description = models.TextField(blank=True, verbose_name="Description")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Créé par")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    # Configuration CI optionnelle
    ci_configuration = models.ForeignKey(
        CIConfiguration, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Configuration CI",
        help_text="Configuration CI pour récupérer automatiquement les résultats"
    )
    
    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Projets"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def has_ci_configuration(self):
        """Vérifie si le projet a une configuration CI"""
        return self.ci_configuration is not None
    
    def get_ci_provider(self):
        """Retourne le fournisseur CI configuré"""
        if self.ci_configuration:
            return self.ci_configuration.provider
        return None
    
    def get_ci_config_details(self):
        """Retourne les détails de la configuration CI"""
        if not self.ci_configuration:
            return None
            
        if self.ci_configuration.provider == 'gitlab':
            return self.ci_configuration.gitlab_config
        elif self.ci_configuration.provider == 'github':
            return self.ci_configuration.github_config
        return None
    
    def get_unique_tags_count(self):
        """Retourne le nombre de tags uniques utilisés dans ce projet"""
        from django.db.models import Count
        return Tag.objects.filter(test__project=self).distinct().count()
    
    def get_total_test_results_count(self):
        """Retourne le nombre total de résultats de tests pour ce projet"""
        return TestResult.objects.filter(execution__project=self).count()
    
    def is_feature_enabled(self, feature_key):
        """Vérifie si une feature est activée pour ce projet"""
        try:
            feature = self.features.get(feature_key=feature_key)
            return feature.is_enabled
        except ProjectFeature.DoesNotExist:
            # Si la feature n'existe pas, retourner la valeur par défaut
            return ProjectFeature.get_default_value(feature_key)


class ProjectFeature(models.Model):
    """Features flags pour personnaliser les fonctionnalités par projet"""
    
    FEATURE_CHOICES = [
        ('evolution_tracking', 'Évolution par rapport à la dernière exécution'),
        # Vous pouvez ajouter d'autres features ici
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='features', verbose_name="Projet")
    feature_key = models.CharField(max_length=50, choices=FEATURE_CHOICES, verbose_name="Feature")
    is_enabled = models.BooleanField(default=True, verbose_name="Activée")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créée le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifiée le")
    
    class Meta:
        verbose_name = "Feature de projet"
        verbose_name_plural = "Features de projet"
        unique_together = ['project', 'feature_key']
        ordering = ['project__name', 'feature_key']
    
    def __str__(self):
        status = "Activée" if self.is_enabled else "Désactivée"
        return f"{self.project.name} - {self.get_feature_key_display()} ({status})"
    
    @classmethod
    def get_default_value(cls, feature_key):
        """Retourne la valeur par défaut pour une feature donnée"""
        defaults = {
            'evolution_tracking': True,  # Par défaut activé
        }
        return defaults.get(feature_key, True)


class Tag(models.Model):
    """Tags pour catégoriser les tests"""
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom du tag")
    color = models.CharField(max_length=7, default="#3b82f6", verbose_name="Couleur")  # Hex color
    
    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class TestExecution(models.Model):
    """Exécution complète de tests (correspond à un JSON de résultats)"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='executions', verbose_name="Projet")
    
    # Données de configuration
    config_file = models.CharField(max_length=500, blank=True, verbose_name="Fichier de configuration")
    root_dir = models.CharField(max_length=500, blank=True, verbose_name="Répertoire racine")
    playwright_version = models.CharField(max_length=50, blank=True, verbose_name="Version Playwright")
    workers = models.IntegerField(default=1, verbose_name="Nombre de workers")
    actual_workers = models.IntegerField(default=1, verbose_name="Workers réels")
    
    # Métadonnées Git
    git_commit_hash = models.CharField(max_length=40, blank=True, verbose_name="Hash du commit")
    git_commit_short_hash = models.CharField(max_length=10, blank=True, verbose_name="Hash court du commit")
    git_branch = models.CharField(max_length=200, blank=True, verbose_name="Branche Git")
    git_commit_subject = models.TextField(blank=True, verbose_name="Sujet du commit")
    git_author_name = models.CharField(max_length=200, blank=True, verbose_name="Auteur")
    git_author_email = models.EmailField(blank=True, verbose_name="Email auteur")
    
    # Métadonnées CI
    ci_build_href = models.URLField(blank=True, verbose_name="Lien vers le build CI")
    ci_commit_href = models.URLField(blank=True, verbose_name="Lien vers le commit CI")
    
    # Statistiques d'exécution
    start_time = models.DateTimeField(verbose_name="Début d'exécution")
    duration = models.FloatField(verbose_name="Durée (ms)")
    expected_tests = models.IntegerField(default=0, verbose_name="Tests attendus")
    skipped_tests = models.IntegerField(default=0, verbose_name="Tests ignorés")
    unexpected_tests = models.IntegerField(default=0, verbose_name="Tests inattendus")
    flaky_tests = models.IntegerField(default=0, verbose_name="Tests instables")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Importé le")
    raw_json = models.JSONField(verbose_name="JSON brut", help_text="Données JSON complètes")
    
    class Meta:
        verbose_name = "Exécution de tests"
        verbose_name_plural = "Exécutions de tests"
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.project.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_tests(self):
        return self.expected_tests + self.skipped_tests + self.unexpected_tests + self.flaky_tests
    
    @property
    def success_rate(self):
        if self.total_tests == 0:
            return 0
        return (self.expected_tests / self.total_tests) * 100


class Test(models.Model):
    """Test unique (peut être exécuté plusieurs fois)"""
    title = models.CharField(max_length=500, verbose_name="Titre du test")
    file_path = models.CharField(max_length=500, verbose_name="Chemin du fichier")
    line = models.IntegerField(verbose_name="Ligne")
    column = models.IntegerField(verbose_name="Colonne")
    
    # Annotations
    test_id = models.CharField(max_length=100, blank=True, verbose_name="ID du test")
    story = models.TextField(blank=True, verbose_name="Histoire/Description")
    comment = models.TextField(blank=True, verbose_name="Commentaire")
    
    # Relations
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tests', verbose_name="Projet")
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="Tags")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    
    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Tests"
        unique_together = ['project', 'title', 'file_path', 'line', 'column']
        ordering = ['file_path', 'line']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'test_id'],
                condition=models.Q(test_id__isnull=False) & ~models.Q(test_id=''),
                name='unique_test_id_per_project'
            )
        ]
    
    def __str__(self):
        return f"{self.title} ({self.file_path}:{self.line})"
    
    def get_latest_result(self):
        """Retourne le dernier résultat d'exécution de ce test"""
        return self.results.order_by('-start_time').first()
    
    def get_latest_status(self):
        """Retourne le statut du dernier résultat d'exécution"""
        latest = self.get_latest_result()
        return latest.status if latest else None
    
    def get_success_rate(self):
        """Calcule le taux de réussite de ce test"""
        total = self.results.count()
        if total == 0:
            return 0
        passed = self.results.filter(status='passed').count()
        return (passed / total) * 100


class TestResult(models.Model):
    """Résultat d'exécution d'un test spécifique"""
    STATUS_CHOICES = [
        ('passed', 'Passé'),
        ('failed', 'Échoué'),
        ('skipped', 'Ignoré'),
        ('flaky', 'Instable'),
        ('expected', 'Attendu'),
        ('unexpected', 'Inattendu'),
    ]
    
    execution = models.ForeignKey(TestExecution, on_delete=models.CASCADE, related_name='test_results', verbose_name="Exécution")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results', verbose_name="Test")
    
    # Informations sur l'exécution
    project_id = models.CharField(max_length=50, verbose_name="ID projet Playwright")
    project_name = models.CharField(max_length=200, verbose_name="Nom projet Playwright")
    timeout = models.IntegerField(verbose_name="Timeout (ms)")
    expected_status = models.CharField(max_length=20, verbose_name="Statut attendu")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Statut")
    
    # Résultats d'exécution
    worker_index = models.IntegerField(verbose_name="Index du worker")
    parallel_index = models.IntegerField(verbose_name="Index parallèle")
    duration = models.FloatField(verbose_name="Durée (ms)")
    retry = models.IntegerField(default=0, verbose_name="Tentative")
    start_time = models.DateTimeField(verbose_name="Début")
    
    # Données brutes
    errors = models.JSONField(default=list, verbose_name="Erreurs")
    stdout = models.JSONField(default=list, verbose_name="Sortie standard")
    stderr = models.JSONField(default=list, verbose_name="Sortie d'erreur")
    steps = models.JSONField(default=list, verbose_name="Étapes")
    annotations = models.JSONField(default=list, verbose_name="Annotations")
    attachments = models.JSONField(default=list, verbose_name="Pièces jointes")
    
    class Meta:
        verbose_name = "Résultat de test"
        verbose_name_plural = "Résultats de tests"
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.test.title} - {self.status} ({self.duration}ms)"
    
    @property
    def has_errors(self):
        return len(self.errors) > 0
    
    @property
    def duration_seconds(self):
        return self.duration / 1000
