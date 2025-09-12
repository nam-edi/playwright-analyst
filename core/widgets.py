from django import forms
from django.forms.widgets import TextInput
from django.forms import utils as forms_utils
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class ColorPickerWidget(TextInput):
    """Widget pour sélectionner une couleur avec un color picker HTML5 et des couleurs prédéfinies"""
    
    input_type = 'color'
    
    # Couleurs prédéfinies organisées par catégories
    PRESET_COLORS = {
        'Bleus': [
            '#1e3a8a', '#1e40af', '#2563eb', '#3b82f6', '#60a5fa', 
            '#93c5fd', '#dbeafe', '#0ea5e9', '#0284c7', '#0369a1'
        ],
        'Verts': [
            '#14532d', '#166534', '#15803d', '#16a34a', '#22c55e', 
            '#4ade80', '#bbf7d0', '#10b981', '#059669', '#047857'
        ],
        'Rouges': [
            '#7f1d1d', '#991b1b', '#dc2626', '#ef4444', '#f87171', 
            '#fca5a5', '#fecaca', '#e11d48', '#be123c', '#9f1239'
        ],
        'Oranges': [
            '#9a3412', '#c2410c', '#ea580c', '#f97316', '#fb923c', 
            '#fdba74', '#fed7aa', '#f59e0b', '#d97706', '#b45309'
        ],
        'Violets': [
            '#581c87', '#6b21a8', '#7c3aed', '#8b5cf6', '#a78bfa', 
            '#c4b5fd', '#e9d5ff', '#a855f7', '#9333ea', '#7e22ce'
        ],
        'Roses': [
            '#831843', '#9d174d', '#be185d', '#db2777', '#ec4899', 
            '#f472b6', '#f9a8d4', '#e879f9', '#d946ef', '#c026d3'
        ],
        'Jaunes': [
            '#92400e', '#a16207', '#ca8a04', '#eab308', '#facc15', 
            '#fde047', '#fef08a', '#f59e0b', '#d97706', '#b45309'
        ],
        'Cyans': [
            '#164e63', '#155e75', '#0891b2', '#0e7490', '#06b6d4', 
            '#22d3ee', '#67e8f9', '#a7f3d0', '#6ee7b7', '#34d399'
        ],
        'Gris': [
            '#111827', '#1f2937', '#374151', '#4b5563', '#6b7280', 
            '#9ca3af', '#d1d5db', '#e5e7eb', '#f3f4f6', '#f9fafb'
        ],
        'Spéciaux': [
            '#fbbf24', '#f472b6', '#34d399', '#60a5fa', '#a78bfa', 
            '#fb7185', '#fbbf24', '#10b981', '#3b82f6', '#8b5cf6'
        ]
    }
    
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
        """Rendu personnalisé avec les couleurs prédéfinies organisées par catégories et couleurs utilisées à droite"""
        # Rendu du widget de base
        if attrs is None:
            attrs = {}
        
        # Ajouter les attributs par défaut
        final_attrs = self.build_attrs(attrs, extra_attrs={'name': name, 'type': self.input_type})
        if value is not None:
            final_attrs['value'] = self.format_value(value)
        
        # Rendu de l'input color
        color_input = format_html('<input{} />', forms_utils.flatatt(final_attrs))
        
        # Obtenir les couleurs déjà utilisées depuis les attributs (passées par le formulaire)
        used_colors = attrs.get('data-used-colors', []) if attrs else []
        
        # Création des sections de couleurs par catégories (couleurs prédéfinies disponibles)
        current_value = self.format_value(value)
        categories_html = []
        
        for category_name, colors in self.PRESET_COLORS.items():
            available_buttons = []
            for color in colors:
                is_selected = color == current_value
                is_used = color in used_colors
                
                # Ne pas afficher les couleurs utilisées dans les catégories prédéfinies
                # sauf si c'est la couleur actuellement sélectionnée
                if is_used and not is_selected:
                    continue
                
                selected_class = ' selected' if is_selected else ''
                
                available_buttons.append(format_html(
                    '<button type="button" class="color-preset{}" '
                    'style="background-color: {};" '
                    'data-color="{}" '
                    'title="{}"></button>',
                    selected_class, color, color, color
                ))
            
            # Ne créer la catégorie que s'il y a des couleurs disponibles
            if available_buttons:
                category_html = format_html(
                    '<div class="color-category">'
                    '<label class="color-category-label">{}</label>'
                    '<div class="color-category-grid">{}</div>'
                    '</div>',
                    category_name, mark_safe(''.join(available_buttons))
                )
                categories_html.append(category_html)
        
        # Créer la section des couleurs utilisées
        used_colors_section = ''
        if used_colors:
            used_buttons = []
            for color in used_colors:
                is_selected = color == current_value
                
                # Pour les couleurs utilisées, elles sont toutes non sélectionnables sauf la couleur actuelle
                selected_class = ' selected' if is_selected else ''
                used_class = ' used' if not is_selected else ''
                disabled_attr = ' disabled' if not is_selected else ''
                
                button_title = color
                if not is_selected:
                    button_title = f"{color} (déjà utilisé)"
                
                used_buttons.append(format_html(
                    '<button type="button" class="color-preset{}{}" '
                    'style="background-color: {};" '
                    'data-color="{}" '
                    'title="{}"{}></button>',
                    selected_class, used_class, color, color, button_title, disabled_attr
                ))
            
            used_colors_section = format_html(
                '<div class="used-colors-container">'
                '<h4 class="used-colors-title">Couleurs déjà utilisées :</h4>'
                '<div class="used-colors-grid">{}</div>'
                '<small class="used-colors-note">💡 Ces couleurs sont déjà utilisées par d\'autres tags de ce projet.</small>'
                '</div>',
                mark_safe(''.join(used_buttons))
            )
        
        # HTML complet avec les couleurs prédéfinies et les couleurs utilisées séparées
        return format_html(
            '<div class="color-picker-widget-container" data-input-name="{}">'
            '<div class="color-picker-main">'
            '<label class="color-picker-label">Couleur sélectionnée :</label>'
            '{}'
            '<span class="color-value">{}</span>'
            '</div>'
            '<div class="color-picker-content">'
            '<div class="color-presets-container">'
            '<h4 class="color-presets-title">Choisir une couleur prédéfinie :</h4>'
            '<div class="color-categories">{}</div>'
            '</div>'
            '{}'
            '</div>'
            '</div>',
            name, color_input, current_value, mark_safe(''.join(categories_html)), used_colors_section
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