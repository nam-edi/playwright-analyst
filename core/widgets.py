from django import forms
from django.forms.widgets import TextInput
from django.forms import utils as forms_utils
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class ColorPickerWidget(TextInput):
    """Widget pour sélectionner une couleur avec un color picker HTML5 et des couleurs prédéfinies"""
    
    input_type = 'color'
    
    # Couleurs prédéfinies populaires
    PRESET_COLORS = [
        '#3b82f6',  # Bleu
        '#ef4444',  # Rouge
        '#10b981',  # Vert
        '#f59e0b',  # Orange
        '#8b5cf6',  # Violet
        '#06b6d4',  # Cyan
        '#84cc16',  # Lime
        '#f97316',  # Orange foncé
        '#ec4899',  # Rose
        '#6b7280',  # Gris
        '#1f2937',  # Gris foncé
        '#dc2626',  # Rouge foncé
    ]
    
    class Media:
        css = {
            'all': ('admin/css/color_picker.css',)
        }
        js = ('admin/js/color_picker.js',)
    
    def __init__(self, attrs=None):
        default_attrs = {
            'style': 'height: 40px; width: 80px; border: 1px solid #ccc; border-radius: 4px; cursor: pointer;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def format_value(self, value):
        """S'assurer que la valeur est au format hexadécimal"""
        if value and not value.startswith('#'):
            return f'#{value}'
        return value or '#3b82f6'
    
    def render(self, name, value, attrs=None, renderer=None):
        """Rendu personnalisé avec les couleurs prédéfinies"""
        # Rendu du widget de base
        if attrs is None:
            attrs = {}
        
        # Ajouter les attributs par défaut
        final_attrs = self.build_attrs(attrs, extra_attrs={'name': name, 'type': self.input_type})
        if value is not None:
            final_attrs['value'] = self.format_value(value)
        
        # Rendu de l'input color
        color_input = format_html('<input{} />', forms_utils.flatatt(final_attrs))
        
        # Création des boutons de couleurs prédéfinies
        current_value = self.format_value(value)
        preset_buttons = []
        
        for color in self.PRESET_COLORS:
            is_selected = color == current_value
            selected_class = ' selected' if is_selected else ''
            preset_buttons.append(format_html(
                '<button type="button" class="color-preset{}" '
                'style="background-color: {};" '
                'data-color="{}" '
                'title="Couleur {}"></button>',
                selected_class, color, color, color
            ))
        
        preset_html = mark_safe(''.join(preset_buttons))
        
        # HTML complet avec les couleurs prédéfinies
        return format_html(
            '<div class="color-picker-widget-container" data-input-name="{}">'
            '<div class="color-picker-main">{}</div>'
            '<div class="color-presets">'
            '<label class="color-presets-label">Couleurs prédéfinies :</label>'
            '<div class="color-presets-grid">{}</div>'
            '</div>'
            '</div>',
            name, color_input, preset_html
        )


class ColorPickerField(forms.CharField):
    """Champ de formulaire pour le sélecteur de couleur"""
    
    widget = ColorPickerWidget
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 7)
        super().__init__(*args, **kwargs)
    
    def clean(self, value):
        """Valider et nettoyer la valeur de couleur"""
        value = super().clean(value)
        if value:
            # S'assurer que la valeur commence par #
            if not value.startswith('#'):
                value = f'#{value}'
            # Valider le format hexadécimal
            if len(value) != 7 or not all(c in '0123456789ABCDEFabcdef' for c in value[1:]):
                raise forms.ValidationError('Veuillez entrer une couleur hexadécimale valide (ex: #FF0000)')
        return value