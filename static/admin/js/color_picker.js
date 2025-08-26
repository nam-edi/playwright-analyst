// JavaScript pour améliorer l'expérience du sélecteur de couleur
(function() {
    'use strict';
    
    function initColorPicker() {
        // Gérer les boutons de couleurs prédéfinies
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('color-preset')) {
                e.preventDefault();
                const color = e.target.getAttribute('data-color');
                const container = e.target.closest('.color-picker-widget-container');
                const inputName = container.getAttribute('data-input-name');
                const colorInput = container.querySelector('input[name="' + inputName + '"]');
                
                if (colorInput) {
                    colorInput.value = color;
                    
                    // Mettre à jour l'état sélectionné
                    container.querySelectorAll('.color-preset').forEach(btn => {
                        btn.classList.remove('selected');
                    });
                    e.target.classList.add('selected');
                    
                    // Déclencher l'événement change
                    colorInput.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
        
        // Améliorer tous les inputs de type color existants (ancien système)
        const colorInputs = document.querySelectorAll('input[type="color"]');
        
        colorInputs.forEach(function(input) {
            // Skip si déjà dans un container moderne
            if (input.closest('.color-picker-widget-container')) {
                return;
            }
            
            // Wrapper le input dans un container avec preview (ancien système)
            if (!input.parentElement.classList.contains('color-picker-widget')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'color-picker-widget';
                
                const preview = document.createElement('span');
                preview.className = 'color-preview';
                preview.style.backgroundColor = input.value;
                
                input.parentNode.insertBefore(wrapper, input);
                wrapper.appendChild(input);
                wrapper.appendChild(preview);
                
                // Mettre à jour la preview quand la couleur change
                input.addEventListener('input', function() {
                    preview.style.backgroundColor = this.value;
                });
                
                input.addEventListener('change', function() {
                    preview.style.backgroundColor = this.value;
                });
            }
        });
        
        // Synchroniser la sélection des couleurs prédéfinies avec le color picker
        const colorContainers = document.querySelectorAll('.color-picker-widget-container');
        colorContainers.forEach(function(container) {
            const inputName = container.getAttribute('data-input-name');
            const colorInput = container.querySelector('input[name="' + inputName + '"]');
            
            if (colorInput) {
                // Synchroniser au chargement
                syncPresetSelection(container, colorInput.value);
                
                // Synchroniser quand l'input change
                colorInput.addEventListener('change', function() {
                    syncPresetSelection(container, this.value);
                });
                
                colorInput.addEventListener('input', function() {
                    syncPresetSelection(container, this.value);
                });
            }
        });
    }
    
    function syncPresetSelection(container, selectedColor) {
        const presetButtons = container.querySelectorAll('.color-preset');
        presetButtons.forEach(function(btn) {
            const btnColor = btn.getAttribute('data-color');
            if (btnColor === selectedColor) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });
    }
    
    // Initialiser au chargement de la page
    document.addEventListener('DOMContentLoaded', initColorPicker);
    
    // Réinitialiser pour les formulaires ajoutés dynamiquement (inline forms)
    document.addEventListener('formset:added', function(event) {
        setTimeout(initColorPicker, 100);
    });
    
    // Pour les anciennes versions de Django
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).on('formset:added', function() {
            setTimeout(initColorPicker, 100);
        });
    }
})();