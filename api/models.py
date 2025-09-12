"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.db import models
from django.contrib.auth.models import User


class APIKey(models.Model):
    """Clé d'API pour l'authentification des endpoints"""
    name = models.CharField(max_length=200, verbose_name="Nom de la clé")
    key = models.CharField(max_length=64, unique=True, verbose_name="Clé API")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys', verbose_name="Utilisateur")
    projects = models.ManyToManyField('projects.Project', blank=True, verbose_name="Projets autorisés", 
                                     help_text="Si vide, accès à tous les projets")
    
    # Permissions
    can_upload = models.BooleanField(default=True, verbose_name="Peut uploader des résultats")
    can_read = models.BooleanField(default=True, verbose_name="Peut lire les données")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créée le")
    last_used = models.DateTimeField(null=True, blank=True, verbose_name="Dernière utilisation")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expire le", 
                                     help_text="Laisser vide pour une clé permanente")
    
    class Meta:
        verbose_name = "Clé API"
        verbose_name_plural = "Clés API"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        if not self.key:
            import secrets
            self.key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def masked_key(self):
        """Retourne une version masquée de la clé pour l'affichage"""
        if len(self.key) <= 8:
            return '*' * len(self.key)
        return self.key[:4] + '*' * (len(self.key) - 8) + self.key[-4:]
    
    def can_access_project(self, project):
        """Vérifie si cette clé peut accéder au projet donné"""
        if not self.is_active or self.is_expired:
            return False
        
        # Si aucun projet spécifié, accès à tous
        if not self.projects.exists():
            return True
        
        # Sinon, vérifier l'autorisation spécifique
        return self.projects.filter(id=project.id).exists()
    
    def update_last_used(self):
        """Met à jour la date de dernière utilisation"""
        from django.utils import timezone
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
