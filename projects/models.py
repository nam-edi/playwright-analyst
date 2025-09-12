"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """Projet contenant plusieurs exécutions de tests"""
    name = models.CharField(max_length=200, verbose_name="Nom du projet")
    description = models.TextField(blank=True, verbose_name="Description")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Créé par")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    # Configuration CI optionnelle - référence vers integrations
    ci_configuration = models.ForeignKey(
        'integrations.CIConfiguration', 
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
        from testing.models import Tag
        from django.db.models import Count
        return Tag.objects.filter(test__project=self).distinct().count()
    
    def get_total_test_results_count(self):
        """Retourne le nombre total de résultats de tests pour ce projet"""
        from testing.models import TestResult
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
        ('tags_mapping', 'Cartographie des tags sur la page d\'accueil'),
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
            'tags_mapping': True,  # Par défaut activé
        }
        return defaults.get(feature_key, True)
