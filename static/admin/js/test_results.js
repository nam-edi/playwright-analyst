// Améliorations pour l'affichage des résultats de tests - Version optimisée
document.addEventListener('DOMContentLoaded', function() {
    initializeTestResultsEnhancements();
});

function initializeTestResultsEnhancements() {
    enhanceTableInteractions();
    addSmartTooltips();
    improveAccessibility();
    enhanceStatusDisplay();
    addKeyboardNavigation();
}

function enhanceTableInteractions() {
    const table = document.querySelector('.results table');
    if (!table) return;

    // Améliorer les liens de tests
    const testLinks = table.querySelectorAll('td a[href*="/test/"], td a[href*="/testresult/"]');
    
    testLinks.forEach(link => {
        // Ajouter des attributs pour une meilleure accessibilité
        if (!link.getAttribute('title') && link.textContent.length > 50) {
            link.setAttribute('title', link.textContent.trim());
        }
        
        // Améliorer la navigation au clavier
        link.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });

    // Ajouter la sélection de lignes au clic
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach((row, index) => {
        row.addEventListener('click', function(e) {
            // Ne pas interférer avec les clics sur les liens ou checkboxes
            if (e.target.tagName === 'A' || e.target.tagName === 'INPUT') {
                return;
            }
            
            // Toggle de sélection de la ligne
            const checkbox = this.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                this.classList.toggle('selected', checkbox.checked);
            }
        });
        
        // Ajouter un numéro de ligne discret
        addRowNumber(row, index + 1);
    });
}

function addRowNumber(row, number) {
    const firstCell = row.querySelector('td:first-child');
    if (!firstCell || firstCell.querySelector('.row-number')) return;
    
    const rowNumber = document.createElement('span');
    rowNumber.className = 'row-number';
    rowNumber.textContent = `#${number}`;
    rowNumber.style.cssText = `
        position: absolute;
        left: -30px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.6rem;
        color: var(--text-muted, #94a3b8);
        font-weight: 500;
        opacity: 0.5;
        pointer-events: none;
    `;
    
    firstCell.style.position = 'relative';
    firstCell.appendChild(rowNumber);
}

function addSmartTooltips() {
    const cellsWithPotentialTruncation = document.querySelectorAll('.results td');
    
    cellsWithPotentialTruncation.forEach(cell => {
        const textElement = cell.querySelector('a') || cell;
        const text = textElement.textContent.trim();
        
        // Ne créer un tooltip que si le texte est vraiment tronqué
        if (text.length > 40 && (textElement.scrollWidth > textElement.clientWidth || text.length > 80)) {
            createSmartTooltip(textElement, text);
        }
    });
}

function createSmartTooltip(element, fullText) {
    let tooltip = null;
    let showTimeout = null;
    let hideTimeout = null;
    
    function showTooltip(e) {
        clearTimeout(hideTimeout);
        showTimeout = setTimeout(() => {
            tooltip = document.createElement('div');
            tooltip.className = 'smart-tooltip';
            tooltip.textContent = fullText;
            tooltip.style.cssText = `
                position: fixed;
                background: var(--text-primary, #1e293b);
                color: var(--bg-primary, #ffffff);
                padding: 0.75rem;
                border-radius: 8px;
                font-size: 0.875rem;
                max-width: 400px;
                z-index: 9999;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                border: 1px solid var(--border-medium, #64748b);
                word-wrap: break-word;
                pointer-events: none;
                opacity: 0;
                transform: translateY(-5px);
                transition: opacity 0.2s ease, transform 0.2s ease;
            `;
            
            document.body.appendChild(tooltip);
            
            // Positionner intelligemment
            const rect = element.getBoundingClientRect();
            const tooltipRect = tooltip.getBoundingClientRect();
            
            let top = rect.bottom + 8;
            let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
            
            // Ajustements pour rester dans la fenêtre
            if (left < 8) left = 8;
            if (left + tooltipRect.width > window.innerWidth - 8) {
                left = window.innerWidth - tooltipRect.width - 8;
            }
            if (top + tooltipRect.height > window.innerHeight - 8) {
                top = rect.top - tooltipRect.height - 8;
            }
            
            tooltip.style.top = top + 'px';
            tooltip.style.left = left + 'px';
            
            // Animation d'apparition
            requestAnimationFrame(() => {
                tooltip.style.opacity = '1';
                tooltip.style.transform = 'translateY(0)';
            });
        }, 500); // Délai avant affichage
    }
    
    function hideTooltip() {
        clearTimeout(showTimeout);
        if (tooltip) {
            hideTimeout = setTimeout(() => {
                tooltip.style.opacity = '0';
                tooltip.style.transform = 'translateY(-5px)';
                setTimeout(() => {
                    if (tooltip && tooltip.parentNode) {
                        tooltip.parentNode.removeChild(tooltip);
                    }
                    tooltip = null;
                }, 200);
            }, 100);
        }
    }
    
    element.addEventListener('mouseenter', showTooltip);
    element.addEventListener('mouseleave', hideTooltip);
    element.addEventListener('focus', showTooltip);
    element.addEventListener('blur', hideTooltip);
}

function improveAccessibility() {
    // Améliorer les contrastes et l'accessibilité
    const table = document.querySelector('.results table');
    if (!table) return;
    
    // Ajouter des en-têtes de portée pour les lecteurs d'écran
    const headers = table.querySelectorAll('th');
    headers.forEach((header, index) => {
        header.setAttribute('scope', 'col');
        header.setAttribute('id', `header-${index}`);
    });
    
    // Améliorer la navigation au clavier dans le tableau
    const cells = table.querySelectorAll('td, th');
    cells.forEach(cell => {
        if (!cell.getAttribute('tabindex') && cell.querySelector('a, input, button')) {
            // Les cellules avec des éléments interactifs
            cell.setAttribute('tabindex', '-1');
        }
    });
}

function enhanceStatusDisplay() {
    // Améliorer l'affichage des statuts avec des icônes et couleurs cohérentes
    const statusElements = document.querySelectorAll('.results td');
    
    statusElements.forEach(cell => {
        const text = cell.textContent.trim().toLowerCase();
        
        // Identifier et améliorer les cellules de statut
        if (text.includes('passé') || text.includes('passed')) {
            enhanceStatusCell(cell, 'passed', '✅', 'Passé');
        } else if (text.includes('échoué') || text.includes('failed')) {
            enhanceStatusCell(cell, 'failed', '❌', 'Échoué');
        } else if (text.includes('ignoré') || text.includes('skipped')) {
            enhanceStatusCell(cell, 'skipped', '⏭️', 'Ignoré');
        } else if (text.includes('instable') || text.includes('flaky')) {
            enhanceStatusCell(cell, 'flaky', '⚠️', 'Instable');
        }
    });
}

function enhanceStatusCell(cell, status, icon, label) {
    if (cell.querySelector('.status-enhanced')) return; // Déjà traité
    
    const statusElement = document.createElement('span');
    statusElement.className = `status-enhanced status-${status}`;
    statusElement.innerHTML = `<span class="status-icon" aria-hidden="true">${icon}</span> <span class="status-text">${label}</span>`;
    statusElement.setAttribute('title', `Statut: ${label}`);
    
    // Remplacer le contenu si c'est juste le texte du statut
    if (cell.textContent.trim().toLowerCase() === label.toLowerCase()) {
        cell.innerHTML = '';
        cell.appendChild(statusElement);
    }
}

function addKeyboardNavigation() {
    // Navigation améliorée au clavier
    document.addEventListener('keydown', function(e) {
        const table = document.querySelector('.results table');
        if (!table) return;
        
        const focused = document.activeElement;
        
        // Navigation avec les flèches dans le tableau
        if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            const cell = focused.closest('td, th');
            if (!cell) return;
            
            const row = cell.parentElement;
            const cellIndex = Array.from(row.children).indexOf(cell);
            
            let targetCell = null;
            
            switch (e.key) {
                case 'ArrowUp':
                    const prevRow = row.previousElementSibling;
                    if (prevRow) targetCell = prevRow.children[cellIndex];
                    break;
                case 'ArrowDown':
                    const nextRow = row.nextElementSibling;
                    if (nextRow) targetCell = nextRow.children[cellIndex];
                    break;
                case 'ArrowLeft':
                    targetCell = cell.previousElementSibling;
                    break;
                case 'ArrowRight':
                    targetCell = cell.nextElementSibling;
                    break;
            }
            
            if (targetCell) {
                e.preventDefault();
                const link = targetCell.querySelector('a, input, button');
                (link || targetCell).focus();
            }
        }
    });
}

// Nettoyer les tooltips lors du changement de page
window.addEventListener('beforeunload', function() {
    document.querySelectorAll('.smart-tooltip').forEach(tooltip => {
        if (tooltip.parentNode) {
            tooltip.parentNode.removeChild(tooltip);
        }
    });
});

// API publique
window.PWAnalystTestResults = {
    initialize: initializeTestResultsEnhancements,
    version: '2.0'
};