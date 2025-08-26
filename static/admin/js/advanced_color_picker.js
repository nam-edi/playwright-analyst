// Advanced Color Picker Widget JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeAdvancedColorPickers();
});

function initializeAdvancedColorPickers() {
    const colorPickers = document.querySelectorAll('.advanced-color-picker');
    
    colorPickers.forEach(picker => {
        const container = picker.parentNode;
        const paletteContainer = container.querySelector('.color-palette-container');
        
        if (paletteContainer) {
            setupColorPalette(picker, paletteContainer);
        }
    });
}

function setupColorPalette(inputElement, paletteContainer) {
    const colorOptions = paletteContainer.querySelectorAll('.color-option');
    
    // Initialize current color selection
    updateSelectedColor(inputElement, paletteContainer);
    
    // Add click listeners to color options
    colorOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.preventDefault();
            const color = this.getAttribute('data-color');
            
            // Update input value
            inputElement.value = color;
            
            // Update visual selection
            updateSelectedColor(inputElement, paletteContainer);
            
            // Trigger change event
            inputElement.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Add selection animation
            this.classList.add('selected');
            setTimeout(() => {
                this.classList.remove('selected');
            }, 300);
        });
        
        // Add hover preview
        option.addEventListener('mouseenter', function() {
            const color = this.getAttribute('data-color');
            previewColor(inputElement, color);
        });
        
        option.addEventListener('mouseleave', function() {
            resetColorPreview(inputElement);
        });
    });
    
    // Listen for manual input changes
    inputElement.addEventListener('input', function() {
        updateSelectedColor(inputElement, paletteContainer);
    });
    
    inputElement.addEventListener('change', function() {
        updateSelectedColor(inputElement, paletteContainer);
    });
}

function updateSelectedColor(inputElement, paletteContainer) {
    const currentColor = inputElement.value.toLowerCase();
    const colorOptions = paletteContainer.querySelectorAll('.color-option');
    
    // Remove previous selections
    colorOptions.forEach(option => {
        option.classList.remove('selected');
    });
    
    // Find and select matching color
    colorOptions.forEach(option => {
        const optionColor = option.getAttribute('data-color').toLowerCase();
        if (optionColor === currentColor) {
            option.classList.add('selected');
        }
    });
    
    // Update input background color for preview
    if (isValidColor(currentColor)) {
        inputElement.style.backgroundColor = currentColor;
        inputElement.style.color = getContrastColor(currentColor);
    } else {
        inputElement.style.backgroundColor = '';
        inputElement.style.color = '';
    }
}

function previewColor(inputElement, color) {
    inputElement.dataset.originalValue = inputElement.value;
    inputElement.value = color;
    inputElement.style.backgroundColor = color;
    inputElement.style.color = getContrastColor(color);
}

function resetColorPreview(inputElement) {
    if (inputElement.dataset.originalValue !== undefined) {
        inputElement.value = inputElement.dataset.originalValue;
        delete inputElement.dataset.originalValue;
        
        const currentColor = inputElement.value;
        if (isValidColor(currentColor)) {
            inputElement.style.backgroundColor = currentColor;
            inputElement.style.color = getContrastColor(currentColor);
        } else {
            inputElement.style.backgroundColor = '';
            inputElement.style.color = '';
        }
    }
}

function isValidColor(color) {
    if (!color) return false;
    
    // Check if it's a valid hex color
    const hexRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
    if (hexRegex.test(color)) return true;
    
    // Check if it's a valid CSS color name
    const tempElement = document.createElement('div');
    tempElement.style.color = color;
    return tempElement.style.color !== '';
}

function getContrastColor(hexColor) {
    // Convert hex to RGB
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    
    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    
    // Return black or white based on luminance
    return luminance > 0.5 ? '#000000' : '#ffffff';
}

// Add color palette toggle functionality
function addColorPaletteToggle() {
    const toggleButtons = document.querySelectorAll('[data-toggle-color-palette]');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-toggle-color-palette');
            const palette = document.getElementById(targetId);
            
            if (palette) {
                palette.style.display = palette.style.display === 'none' ? 'block' : 'none';
            }
        });
    });
}

// Initialize color history functionality
function initializeColorHistory() {
    const STORAGE_KEY = 'pw_analyst_color_history';
    const MAX_HISTORY = 10;
    
    function getColorHistory() {
        const history = localStorage.getItem(STORAGE_KEY);
        return history ? JSON.parse(history) : [];
    }
    
    function addToColorHistory(color) {
        let history = getColorHistory();
        
        // Remove if already exists
        history = history.filter(c => c !== color);
        
        // Add to beginning
        history.unshift(color);
        
        // Limit size
        history = history.slice(0, MAX_HISTORY);
        
        localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
        updateColorHistoryDisplay();
    }
    
    function updateColorHistoryDisplay() {
        const historyContainers = document.querySelectorAll('.color-history');
        const history = getColorHistory();
        
        historyContainers.forEach(container => {
            container.innerHTML = '';
            
            if (history.length > 0) {
                const title = document.createElement('label');
                title.textContent = 'Récemment utilisées';
                container.appendChild(title);
                
                const grid = document.createElement('div');
                grid.className = 'color-grid';
                
                history.forEach(color => {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'color-option';
                    button.setAttribute('data-color', color);
                    button.style.backgroundColor = color;
                    button.title = color;
                    grid.appendChild(button);
                });
                
                container.appendChild(grid);
            }
        });
    }
    
    // Listen for color selections to add to history
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('advanced-color-picker')) {
            const color = e.target.value;
            if (isValidColor(color)) {
                addToColorHistory(color);
            }
        }
    });
    
    updateColorHistoryDisplay();
}

// Export functions for external use
window.PWAnalystColorPicker = {
    initialize: initializeAdvancedColorPickers,
    addToHistory: function(color) {
        // This will be called when initializeColorHistory is set up
    }
};