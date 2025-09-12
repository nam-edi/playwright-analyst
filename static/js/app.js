// Configuration et scripts personnalisés HTMX

document.addEventListener('DOMContentLoaded', function() {
    // Configuration HTMX globale
    if (typeof htmx !== 'undefined') {
        // Configuration des headers CSRF pour Django
        htmx.config.useTemplateFragments = true;

        // Event listeners HTMX
        document.body.addEventListener('htmx:configRequest', function(evt) {
            // Ajouter le token CSRF à toutes les requêtes
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfToken) {
                evt.detail.headers['X-CSRFToken'] = csrfToken.value;
            }
        });

        document.body.addEventListener('htmx:afterSwap', function(evt) {
            // Ajouter une animation fade-in après le swap
            evt.detail.target.classList.add('fade-in');

            // Si le target est le panneau de détail, l'ouvrir automatiquement
            if (evt.detail.target.id === 'test-detail-panel') {
                openTestPanel();
            }
        });

        document.body.addEventListener('htmx:responseError', function(evt) {
            console.error('Erreur HTMX:', evt.detail);
        });
    }
});

// Fonctions utilitaires
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Fonctions pour le panneau latéral des détails de test (scope global)
window.openTestPanel = function() {
    const panel = document.getElementById('test-detail-panel');
    const overlay = document.getElementById('panel-overlay');

    if (panel && overlay) {
        panel.style.display = 'block';
        overlay.classList.remove('hidden');

        // Animation d'ouverture
        setTimeout(() => {
            panel.classList.remove('translate-x-full');
            panel.classList.add('translate-x-0');
        }, 10);

        // Empêcher le scroll du body
        document.body.style.overflow = 'hidden';
    }
};

window.closeTestPanel = function() {
    const panel = document.getElementById('test-detail-panel');
    const overlay = document.getElementById('panel-overlay');

    if (panel && overlay) {
        // Animation de fermeture
        panel.classList.remove('translate-x-0');
        panel.classList.add('translate-x-full');

        setTimeout(() => {
            panel.style.display = 'none';
            overlay.classList.add('hidden');
            // Restaurer le scroll du body
            document.body.style.overflow = '';
        }, 300);
    }
};

// Fermer le panneau avec la touche Échap
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeTestPanel();
    }
});
