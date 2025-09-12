// JavaScript pour améliorer l'expérience du sélecteur de couleur
(function() {
    'use strict';
    
    function initColorPicker() {
        // Compter les widgets présents
        const containers = document.querySelectorAll('.color-picker-widget-container');
        const usedColorsSections = document.querySelectorAll('.used-colors-container');
        // Gérer les boutons de couleurs prédéfinies
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('color-preset')) {
                e.preventDefault();
                
                // Ne pas permettre la sélection des couleurs déjà utilisées
                if (e.target.classList.contains('used')) {
                    // Afficher une alerte ou un message d'erreur
                    showColorUsedMessage(e.target);
                    return;
                }
                
                const color = e.target.getAttribute('data-color');
                const container = e.target.closest('.color-picker-widget-container');
                const inputName = container.getAttribute('data-input-name');
                const colorInput = container.querySelector('input[name="' + inputName + '"]');
                const colorValue = container.querySelector('.color-value');
                
                if (colorInput) {
                    colorInput.value = color;
                    
                    // Mettre à jour l'affichage de la valeur
                    if (colorValue) {
                        colorValue.textContent = color;
                    }
                    
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
            const colorValue = container.querySelector('.color-value');
            
            if (colorInput) {
                // Synchroniser au chargement
                syncPresetSelection(container, colorInput.value);
                updateColorValue(colorValue, colorInput.value);
                
                // Synchroniser quand l'input change
                colorInput.addEventListener('change', function() {
                    syncPresetSelection(container, this.value);
                    updateColorValue(colorValue, this.value);
                });
                
                colorInput.addEventListener('input', function() {
                    syncPresetSelection(container, this.value);
                    updateColorValue(colorValue, this.value);
                });
            }
        });
        
        // Appliquer display: flex à la div parent de id_color_helptext
        const colorHelptextElement = document.getElementById('id_color_helptext');
        if (colorHelptextElement && colorHelptextElement.parentElement) {
            colorHelptextElement.parentElement.style.display = 'flex';
        }
        
        // Ajouter des croix visuelles sur les couleurs déjà utilisées
        setTimeout(function() {
            addCrossesToUsedColors();
        }, 200);
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
    
    function updateColorValue(colorValueElement, color) {
        if (colorValueElement) {
            colorValueElement.textContent = color;
        }
    }
    
    function addCrossesToUsedColors() {
        // Chercher le texte d'aide pour les couleurs utilisées
        const colorHelptextElement = document.getElementById('id_color_helptext');
        if (colorHelptextElement) {
            // Extraire les couleurs hexadécimales du texte d'aide
            const hexColorRegex = /#[a-fA-F0-9]{6}/g;
            const usedColorsFromText = colorHelptextElement.textContent.match(hexColorRegex) || [];
            
            if (usedColorsFromText.length > 0) {
                // Parcourir tous les presets de couleurs prédéfinies
                const allPresets = document.querySelectorAll('.color-presets-container .color-preset');
                
                allPresets.forEach(function(preset) {
                    const presetColor = preset.getAttribute('data-color');
                    if (usedColorsFromText.includes(presetColor)) {
                        // Vérifier si la croix n'existe pas déjà
                        if (!preset.querySelector('.used-cross')) {
                            // Marquer comme utilisé
                            preset.classList.add('used');
                            
                            // Créer l'élément croix
                            const cross = document.createElement('span');
                            cross.className = 'used-cross';
                            cross.innerHTML = '✕';
                            cross.style.cssText = `
                                position: absolute;
                                top: 50%;
                                left: 50%;
                                transform: translate(-50%, -50%);
                                color: #dc2626;
                                font-weight: bold;
                                font-size: 16px;
                                text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                                z-index: 3;
                                pointer-events: none;
                            `;
                            
                            // Ajouter la croix au preset
                            preset.appendChild(cross);
                            
                            // S'assurer que le preset a une position relative
                            if (getComputedStyle(preset).position === 'static') {
                                preset.style.position = 'relative';
                            }
                        }
                    }
                });
                
                return; // Sortir de la fonction si on a trouvé et traité les couleurs
            }
        }
        
        // Approche secondaire : identifier les couleurs utilisées dans les sections prédéfinies
        const usedColorsSection = document.querySelector('.used-colors-container');
        if (usedColorsSection) {
            const usedColorElements = usedColorsSection.querySelectorAll('.color-preset');
            const usedColorValues = Array.from(usedColorElements).map(el => el.getAttribute('data-color'));
            
            // Parcourir tous les presets de couleurs prédéfinies
            const allPresets = document.querySelectorAll('.color-presets-container .color-preset');
            
            allPresets.forEach(function(preset) {
                const presetColor = preset.getAttribute('data-color');
                if (usedColorValues.includes(presetColor)) {
                    // Vérifier si la croix n'existe pas déjà
                    if (!preset.querySelector('.used-cross')) {
                        // Marquer comme utilisé
                        preset.classList.add('used');
                        
                        // Créer l'élément croix
                        const cross = document.createElement('span');
                        cross.className = 'used-cross';
                        cross.innerHTML = '✕';
                        cross.style.cssText = `
                            position: absolute;
                            top: 50%;
                            left: 50%;
                            transform: translate(-50%, -50%);
                            color: #dc2626;
                            font-weight: bold;
                            font-size: 16px;
                            text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                            z-index: 3;
                            pointer-events: none;
                        `;
                        
                        // Ajouter la croix au preset
                        preset.appendChild(cross);
                        
                        // S'assurer que le preset a une position relative
                        if (getComputedStyle(preset).position === 'static') {
                            preset.style.position = 'relative';
                        }
                    }
                }
            });
        }
        
        // Vérification supplémentaire : chercher les éléments déjà marqués .used
        const alreadyUsedPresets = document.querySelectorAll('.color-preset.used');
        
        alreadyUsedPresets.forEach(function(preset) {
            if (!preset.querySelector('.used-cross')) {
                const cross = document.createElement('span');
                cross.className = 'used-cross';
                cross.innerHTML = '✕';
                cross.style.cssText = `
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: #dc2626;
                    font-weight: bold;
                    font-size: 16px;
                    text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.8);
                    z-index: 3;
                    pointer-events: none;
                `;
                
                preset.appendChild(cross);
                
                if (getComputedStyle(preset).position === 'static') {
                    preset.style.position = 'relative';
                }
            }
        });
    }
    
    function showColorUsedMessage(colorButton) {
        const color = colorButton.getAttribute('data-color');
        
        // Créer une notification temporaire
        const notification = document.createElement('div');
        notification.className = 'color-used-notification';
        notification.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: #dc2626;
                color: white;
                padding: 12px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                z-index: 10000;
                animation: slideIn 0.3s ease-out;
            ">
                ⚠️ La couleur ${color} est déjà utilisée dans ce projet
            </div>
        `;
        
        // Ajouter l'animation CSS si elle n'existe pas
        if (!document.querySelector('#color-picker-animations')) {
            const style = document.createElement('style');
            style.id = 'color-picker-animations';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(notification);
        
        // Supprimer la notification après 3 secondes
        setTimeout(() => {
            if (notification.parentNode) {
                const notificationDiv = notification.querySelector('div');
                notificationDiv.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }
        }, 3000);
    }
    
    // Ajouter des effets visuels pour améliorer l'UX
    function addVisualEffects() {
        const containers = document.querySelectorAll('.color-picker-widget-container');
        
        containers.forEach(function(container) {
            const presets = container.querySelectorAll('.color-preset');
            
            presets.forEach(function(preset) {
                // Effet de hover avec info-bulle
                preset.addEventListener('mouseenter', function() {
                    const tooltip = document.createElement('div');
                    tooltip.className = 'color-tooltip';
                    tooltip.textContent = this.getAttribute('data-color');
                    tooltip.style.cssText = `
                        position: absolute;
                        background: #333;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        top: -30px;
                        left: 50%;
                        transform: translateX(-50%);
                        z-index: 1000;
                        white-space: nowrap;
                        pointer-events: none;
                    `;
                    this.style.position = 'relative';
                    this.appendChild(tooltip);
                });
                
                preset.addEventListener('mouseleave', function() {
                    const tooltip = this.querySelector('.color-tooltip');
                    if (tooltip) {
                        tooltip.remove();
                    }
                });
            });
        });
    }
    
    // Initialiser au chargement de la page
    document.addEventListener('DOMContentLoaded', function() {
        initColorPicker();
        addVisualEffects();
        addCrossesToUsedColors();
    });
    
    // Réinitialiser pour les formulaires ajoutés dynamiquement (inline forms)
    document.addEventListener('formset:added', function(event) {
        setTimeout(function() {
            initColorPicker();
            addVisualEffects();
            addCrossesToUsedColors();
        }, 100);
    });
    
    // Pour les anciennes versions de Django
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).on('formset:added', function() {
            setTimeout(function() {
                initColorPicker();
                addVisualEffects();
                addCrossesToUsedColors();
            }, 100);
        });
    }
})();