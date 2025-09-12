"""
PW Analyst - Playwright Test Results Analyzer
Copyright (c) 2025 Damien Hoffmann

This work is licensed under CC BY-NC-SA 4.0
https://creativecommons.org/licenses/by-nc-sa/4.0/
"""

from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.contrib import messages
from datetime import timedelta
from .models import APIKey


class APIKeyForm(forms.ModelForm):
    """Formulaire personnalisé pour APIKey avec clé masquée et régénération"""
    
    regenerate_key = forms.BooleanField(
        required=False,
        label='Régénérer la clé API',
        help_text='⚠️ Attention : Cocher cette case générera une nouvelle clé et invalidera l\'ancienne définitivement !',
        widget=forms.CheckboxInput(attrs={'style': 'transform: scale(1.2); margin-right: 8px;'})
    )
    
    class Meta:
        model = APIKey
        exclude = ['key']  # Exclure complètement le champ key du formulaire
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Gérer la régénération de clé
        if self.cleaned_data.get('regenerate_key'):
            import secrets
            instance.key = secrets.token_urlsafe(32)
        elif self.instance.pk:
            # Conserver l'ancienne clé si pas de régénération
            old_instance = APIKey.objects.get(pk=self.instance.pk)
            instance.key = old_instance.key
        
        if commit:
            instance.save()
        return instance


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    form = APIKeyForm
    list_display = ['name', 'user', 'masked_key', 'projects_count', 'permissions_display', 'is_active', 'last_used', 'expires_at']
    list_filter = ['is_active', 'can_upload', 'can_read', 'created_at', 'expires_at']
    search_fields = ['name', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'last_used', 'masked_key']
    filter_horizontal = ['projects']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'user', 'masked_key')
        }),
        ('Régénération', {
            'fields': ('regenerate_key',),
            'description': 'Cochez cette case pour générer une nouvelle clé API. L\'ancienne clé sera immédiatement invalidée.',
            'classes': ('wide',)
        }),
        ('Permissions', {
            'fields': ('can_upload', 'can_read', 'projects'),
            'description': 'Si aucun projet n\'est sélectionné, la clé aura accès à tous les projets.'
        }),
        ('État', {
            'fields': ('is_active', 'expires_at')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'last_used'),
            'classes': ('collapse',)
        })
    )
    
    def get_fieldsets(self, request, obj=None):
        """Personnalise les fieldsets selon le contexte"""
        if obj:  # Modification
            return self.fieldsets
        else:  # Création
            return (
                ('Informations générales', {
                    'fields': ('name', 'user')
                }),
                ('Permissions', {
                    'fields': ('can_upload', 'can_read', 'projects'),
                    'description': 'Si aucun projet n\'est sélectionné, la clé aura accès à tous les projets.'
                }),
                ('État', {
                    'fields': ('is_active', 'expires_at')
                })
            )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('projects')
    
    def save_model(self, request, obj, form, change):
        """Gérer la création et régénération de clés"""
        if not change:  # Nouveau modèle
            obj.user = obj.user or request.user
        
        # Vérifier si une régénération est demandée
        regenerate_requested = form.cleaned_data.get('regenerate_key', False)
        
        super().save_model(request, obj, form, change)
        
        # Messages informatifs
        if not change:
            messages.success(
                request,
                f'🎉 Clé API créée avec succès ! Voici la clé complète (notez-la, elle ne sera plus affichée) : {obj.key}'
            )
        elif regenerate_requested:
            messages.warning(
                request,
                f'🔄 Clé API régénérée avec succès ! Nouvelle clé : {obj.key} (⚠️ L\'ancienne clé est maintenant invalidée)'
            )
    
    def projects_count(self, obj):
        """Affiche le nombre de projets autorisés"""
        count = obj.projects.count()
        if count == 0:
            return format_html('<span style="color: #10b981;">Tous les projets</span>')
        return format_html('<span title="Projets spécifiques">{} projet(s)</span>', count)
    projects_count.short_description = 'Projets autorisés'
    
    def permissions_display(self, obj):
        """Affiche les permissions de façon lisible"""
        perms = []
        if obj.can_read:
            perms.append('📖 Lecture')
        if obj.can_upload:
            perms.append('📤 Upload')
        
        if not perms:
            return format_html('<span style="color: #ef4444;">Aucune permission</span>')
        
        return format_html('<span title="{}">{}</span>', ', '.join(perms), ' + '.join(perms))
    permissions_display.short_description = 'Permissions'
    
    def masked_key(self, obj):
        """Affiche la clé masquée"""
        if obj.key:
            return format_html('<code style="font-family: monospace;">{}</code>', obj.masked_key)
        return "-"
    masked_key.short_description = 'Clé (masquée)'
    
    actions = ['deactivate_keys', 'extend_expiry']
    
    @admin.action(description='Désactiver les clés sélectionnées')
    def deactivate_keys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} clé(s) API désactivée(s).',
            messages.SUCCESS
        )
    
    @admin.action(description='Prolonger l\'expiration de 30 jours')
    def extend_expiry(self, request, queryset):
        from django.utils import timezone
        new_expiry = timezone.now() + timedelta(days=30)
        updated = queryset.update(expires_at=new_expiry)
        self.message_user(
            request,
            f'Expiration prolongée pour {updated} clé(s) API (nouveau délai : {new_expiry.strftime("%d/%m/%Y")}).',
            messages.SUCCESS
        )
