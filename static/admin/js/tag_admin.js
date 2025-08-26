// Tag Admin Enhancements for PW Analyst

document.addEventListener('DOMContentLoaded', function() {
    enhanceTagDisplay();
    initializeTagColorPreview();
    addTagUtilities();
});

function enhanceTagDisplay() {
    // Améliorer l'affichage des tags dans les listes
    const tagCells = document.querySelectorAll('td:has(.admin-tag-color)');
    
    tagCells.forEach(cell => {
        const tagElements = cell.querySelectorAll('.admin-tag-color');
        
        tagElements.forEach(tag => {
            const dot = tag.querySelector('.admin-tag-color-dot');
            if (dot) {
                const bgColor = dot.style.backgroundColor;
                if (bgColor) {
                    // Appliquer la couleur de fond au tag entier avec transparence
                    const rgba = hexToRgba(bgColor, 0.1);
                    tag.style.backgroundColor = rgba;
                    tag.style.border = `1px solid ${bgColor}`;
                }
            }
        });
    });
}

function initializeTagColorPreview() {
    // Prévisualisation en temps réel des couleurs de tags
    const colorInputs = document.querySelectorAll('input[name$="color"]');
    
    colorInputs.forEach(input => {
        // Ajouter un aperçu à côté du champ
        const preview = document.createElement('div');
        preview.className = 'tag-color-preview';
        preview.style.cssText = `
            display: inline-block;
            width: 40px;
            height: 40px;
            border-radius: 8px;
            border: 2px solid #e2e8f0;
            margin-left: 0.5rem;
            vertical-align: middle;
            transition: all 0.2s ease;
        `;
        
        input.parentNode.insertBefore(preview, input.nextSibling);
        
        // Mettre à jour l'aperçu
        function updatePreview() {
            const color = input.value;
            if (isValidColor(color)) {
                preview.style.backgroundColor = color;
                preview.style.borderColor = color;
                preview.title = `Couleur: ${color}`;
            } else {
                preview.style.backgroundColor = '#f8fafc';
                preview.style.borderColor = '#e2e8f0';
                preview.title = 'Couleur invalide';
            }
        }
        
        // Initialiser et écouter les changements
        updatePreview();
        input.addEventListener('input', updatePreview);
        input.addEventListener('change', updatePreview);
    });
}

function addTagUtilities() {
    // Ajouter des utilitaires pour la gestion des tags
    const tagForm = document.querySelector('form[action*="tag"]');
    
    if (tagForm) {
        addColorSuggestions(tagForm);
        addTagPreview(tagForm);
    }
}

function addColorSuggestions(form) {
    const colorInput = form.querySelector('input[name$="color"]');
    if (!colorInput) return;
    
    // Créer un conteneur pour les suggestions
    const suggestions = document.createElement('div');
    suggestions.className = 'color-suggestions';
    suggestions.innerHTML = `
        <label>Couleurs suggérées:</label>
        <div class="suggestion-grid">
            <button type="button" data-color="#ef4444" title="Rouge - Erreurs">🔴</button>
            <button type="button" data-color="#f59e0b" title="Orange - Avertissements">🟠</button>
            <button type="button" data-color="#10b981" title="Vert - Succès">🟢</button>
            <button type="button" data-color="#3b82f6" title="Bleu - Information">🔵</button>
            <button type="button" data-color="#8b5cf6" title="Violet - Fonctionnalité">🟣</button>
            <button type="button" data-color="#ec4899" title="Rose - UI/UX">🩷</button>
            <button type="button" data-color="#06b6d4" title="Cyan - API">🐈‍⬛</button>
            <button type="button" data-color="#84cc16" title="Lime - Performance">🟢</button>
        </div>
    `;
    
    suggestions.style.cssText = `
        margin-top: 1rem;
        padding: 1rem;
        background-color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    `;
    
    const gridStyle = `
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.5rem;
        margin-top: 0.5rem;
    `;
    
    const buttonStyle = `
        padding: 0.75rem;
        border: 2px solid #e2e8f0;
        border-radius: 6px;
        background: white;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 1.5rem;
    `;
    
    suggestions.querySelector('.suggestion-grid').style.cssText = gridStyle;
    
    const buttons = suggestions.querySelectorAll('button[data-color]');
    buttons.forEach(button => {
        button.style.cssText = buttonStyle;
        
        button.addEventListener('click', function() {
            const color = this.getAttribute('data-color');
            colorInput.value = color;
            colorInput.dispatchEvent(new Event('input', { bubbles: true }));
            colorInput.dispatchEvent(new Event('change', { bubbles: true }));
        });
        
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
            this.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
            this.style.boxShadow = 'none';
        });
    });
    
    colorInput.parentNode.appendChild(suggestions);
}

function addTagPreview(form) {
    const nameInput = form.querySelector('input[name$="name"]');
    const colorInput = form.querySelector('input[name$="color"]');
    
    if (!nameInput || !colorInput) return;
    
    // Créer un aperçu du tag
    const preview = document.createElement('div');
    preview.className = 'tag-preview';
    preview.innerHTML = `
        <label>Aperçu du tag:</label>
        <div class="preview-tag">
            <span class="preview-dot"></span>
            <span class="preview-name">Nom du tag</span>
        </div>
    `;
    
    preview.style.cssText = `
        margin-top: 1rem;
        padding: 1rem;
        background-color: #f0f9ff;
        border-radius: 8px;
        border: 1px solid #0ea5e9;
    `;
    
    const previewTag = preview.querySelector('.preview-tag');
    previewTag.style.cssText = `
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        background-color: white;
        border: 1px solid #e2e8f0;
        margin-top: 0.5rem;
    `;
    
    const previewDot = preview.querySelector('.preview-dot');
    previewDot.style.cssText = `
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: 1px solid rgba(255, 255, 255, 0.8);
    `;
    
    const previewName = preview.querySelector('.preview-name');
    previewName.style.cssText = `
        font-weight: 500;
        color: #1e293b;
    `;
    
    function updatePreview() {
        const name = nameInput.value || 'Nom du tag';
        const color = colorInput.value || '#6b7280';
        
        previewName.textContent = name;
        previewDot.style.backgroundColor = color;
        
        if (isValidColor(color)) {
            const rgba = hexToRgba(color, 0.1);
            previewTag.style.backgroundColor = rgba;
            previewTag.style.borderColor = color;
        }
    }
    
    nameInput.addEventListener('input', updatePreview);
    colorInput.addEventListener('input', updatePreview);
    
    updatePreview();
    
    form.appendChild(preview);
}

// Fonctions utilitaires
function isValidColor(color) {
    if (!color) return false;
    
    const hexRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
    return hexRegex.test(color);
}

function hexToRgba(hex, alpha = 1) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (result) {
        const r = parseInt(result[1], 16);
        const g = parseInt(result[2], 16);
        const b = parseInt(result[3], 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    return hex;
}

// Export pour utilisation externe
window.PWAnalystTagAdmin = {
    enhanceTagDisplay,
    initializeTagColorPreview,
    addTagUtilities
};