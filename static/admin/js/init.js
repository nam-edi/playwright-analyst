// Initialisation globale des améliorations admin
(function() {
    'use strict';

    // Configuration
    const config = {
        debug: false,
        features: {
            testResults: true,
            tooltips: true,
            navigation: true,
            accessibility: true
        }
    };

    // Logger pour debug
    const logger = {
        info: (msg) => config.debug && console.log('[PW-Analyst]', msg),
        warn: (msg) => console.warn('[PW-Analyst]', msg),
        error: (msg) => console.error('[PW-Analyst]', msg)
    };

    // Détection des pages admin
    function detectPage() {
        const path = window.location.pathname;
        const body = document.body;

        if (path.includes('/admin/core/testresult/')) {
            return 'test-results';
        } else if (path.includes('/admin/core/tag/')) {
            return 'tags';
        } else if (path.includes('/admin/core/testexecution/')) {
            return 'executions';
        } else if (path.includes('/admin/')) {
            return 'admin';
        }

        return 'unknown';
    }

    // Initialisation des fonctionnalités
    function initializeFeatures(pageType) {
        logger.info(`Initializing features for page: ${pageType}`);

        // Test Results
        if (pageType === 'test-results' && config.features.testResults) {
            if (window.PWAnalystTestResults) {
                window.PWAnalystTestResults.initialize();
                logger.info('Test results enhancements initialized');
            }
        }

        // Tooltips globaux
        if (config.features.tooltips) {
            initializeGlobalTooltips();
        }

        // Navigation améliorée
        if (config.features.navigation) {
            enhanceNavigation();
        }

        // Accessibilité
        if (config.features.accessibility) {
            enhanceAccessibility();
        }
    }

    function initializeGlobalTooltips() {
        // Tooltips pour éléments avec title
        const elementsWithTitle = document.querySelectorAll('[title]');
        elementsWithTitle.forEach(element => {
            const title = element.getAttribute('title');
            if (title && title.length > 30) {
                element.addEventListener('mouseenter', function(e) {
                    showTooltip(e.target, title);
                });
                element.addEventListener('mouseleave', hideTooltip);
            }
        });
    }

    function enhanceNavigation() {
        // Améliorer la navigation au clavier
        const links = document.querySelectorAll('a, button, [tabindex]');
        links.forEach(link => {
            link.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && this.tagName !== 'BUTTON') {
                    e.preventDefault();
                    this.click();
                }
            });
        });

        // Navigation avec touches fléchées dans les tableaux
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            table.addEventListener('keydown', handleTableNavigation);
        });
    }

    function handleTableNavigation(e) {
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
            return;
        }

        const cell = e.target.closest('td, th');
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
            const focusable = targetCell.querySelector('a, input, button') || targetCell;
            focusable.focus();
        }
    }

    function enhanceAccessibility() {
        // Ajouter des labels ARIA manquants
        const inputs = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
        inputs.forEach(input => {
            const label = input.closest('div').querySelector('label');
            if (label && !input.getAttribute('aria-label')) {
                input.setAttribute('aria-label', label.textContent.trim());
            }
        });

        // Améliorer les contrastes
        enhanceContrasts();

        // Skip links
        addSkipLinks();
    }

    function enhanceContrasts() {
        // Vérifier et améliorer les contrastes faibles
        const lowContrastElements = document.querySelectorAll('.text-muted, .help-text');
        lowContrastElements.forEach(element => {
            const styles = getComputedStyle(element);
            const color = styles.color;

            // Si la couleur est trop claire, l'assombrir légèrement
            if (color.includes('rgb(148, 163, 184)')) { // text-muted
                element.style.color = 'rgb(100, 116, 139)'; // Plus sombre
            }
        });
    }

    function addSkipLinks() {
        if (document.querySelector('.skip-links')) return;

        const skipLinks = document.createElement('div');
        skipLinks.className = 'skip-links';
        skipLinks.innerHTML = `
            <a href="#main-content" class="skip-link">Aller au contenu principal</a>
            <a href="#navigation" class="skip-link">Aller à la navigation</a>
        `;

        skipLinks.style.cssText = `
            position: fixed;
            top: -100px;
            left: 0;
            z-index: 9999;
            background: #000;
            color: #fff;
            padding: 0.5rem;
            transition: top 0.2s ease;
        `;

        const skipLinkStyle = `
            .skip-link:focus {
                top: 0 !important;
                position: fixed !important;
                z-index: 10000 !important;
            }
        `;

        const style = document.createElement('style');
        style.textContent = skipLinkStyle;
        document.head.appendChild(style);

        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    // Système de tooltip simple
    let currentTooltip = null;

    function showTooltip(element, text) {
        hideTooltip();

        const tooltip = document.createElement('div');
        tooltip.className = 'global-tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: fixed;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.875rem;
            max-width: 300px;
            z-index: 10000;
            pointer-events: none;
            word-wrap: break-word;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            opacity: 0;
            transition: opacity 0.2s ease;
        `;

        document.body.appendChild(tooltip);

        // Positionner
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let top = rect.bottom + 8;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

        // Ajustements
        if (left < 8) left = 8;
        if (left + tooltipRect.width > window.innerWidth - 8) {
            left = window.innerWidth - tooltipRect.width - 8;
        }
        if (top + tooltipRect.height > window.innerHeight - 8) {
            top = rect.top - tooltipRect.height - 8;
        }

        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';

        requestAnimationFrame(() => {
            tooltip.style.opacity = '1';
        });

        currentTooltip = tooltip;
    }

    function hideTooltip() {
        if (currentTooltip) {
            currentTooltip.style.opacity = '0';
            setTimeout(() => {
                if (currentTooltip && currentTooltip.parentNode) {
                    currentTooltip.parentNode.removeChild(currentTooltip);
                }
                currentTooltip = null;
            }, 200);
        }
    }

    // Gestion des erreurs
    function handleError(error) {
        logger.error('Initialization error:', error);
        // Ne pas bloquer l'interface en cas d'erreur
    }

    // Point d'entrée principal
    function initialize() {
        try {
            const pageType = detectPage();
            logger.info(`Page detected: ${pageType}`);

            // Attendre que le DOM soit complètement chargé
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    initializeFeatures(pageType);
                });
            } else {
                initializeFeatures(pageType);
            }

            // Réinitialiser après navigation AJAX
            let lastUrl = location.href;
            new MutationObserver(() => {
                const url = location.href;
                if (url !== lastUrl) {
                    lastUrl = url;
                    setTimeout(() => {
                        const newPageType = detectPage();
                        initializeFeatures(newPageType);
                    }, 100);
                }
            }).observe(document, { subtree: true, childList: true });

        } catch (error) {
            handleError(error);
        }
    }

    // Export pour debug
    window.PWAnalystInit = {
        initialize,
        config,
        logger,
        version: '1.0'
    };

    // Auto-initialisation
    initialize();

})();
