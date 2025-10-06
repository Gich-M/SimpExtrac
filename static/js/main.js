// SimpExtrac - Main JavaScript for HTMX Enhancement
document.addEventListener('DOMContentLoaded', function() {
    
    // Global HTMX Configuration
    htmx.config.globalViewTransitions = true;
    htmx.config.defaultSwapStyle = 'innerHTML';
    htmx.config.defaultSwapDelay = 100;
    htmx.config.defaultSettleDelay = 100;

    // Enhanced loading states
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const target = evt.target;
        
        // Show global loading indicator
        const globalLoader = document.getElementById('loading-indicator');
        if (globalLoader) {
            globalLoader.classList.remove('hidden');
            globalLoader.style.display = 'flex';
        }
        
        // Add loading class to buttons
        if (target.tagName === 'BUTTON' || target.classList.contains('btn')) {
            target.classList.add('loading');
            target.disabled = true;
            
            // Store original text
            const originalText = target.innerHTML;
            target.dataset.originalText = originalText;
            
            // Add spinner
            target.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        }
        
        // Add loading class to forms
        if (target.tagName === 'FORM') {
            target.classList.add('htmx-loading');
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const target = evt.target;
        
        // Hide global loading indicator
        const globalLoader = document.getElementById('loading-indicator');
        if (globalLoader) {
            globalLoader.classList.add('hidden');
            globalLoader.style.display = 'none';
        }
        
        // Remove loading state from buttons
        if (target.tagName === 'BUTTON' || target.classList.contains('btn')) {
            target.classList.remove('loading');
            target.disabled = false;
            
            // Restore original text
            if (target.dataset.originalText) {
                target.innerHTML = target.dataset.originalText;
                delete target.dataset.originalText;
            }
        }
        
        // Remove loading class from forms
        if (target.tagName === 'FORM') {
            target.classList.remove('htmx-loading');
        }
    });

    // Auto-refresh functionality
    function setupAutoRefresh() {
        const autoRefreshElements = document.querySelectorAll('[data-auto-refresh]');
        autoRefreshElements.forEach(element => {
            const interval = parseInt(element.dataset.autoRefresh) || 30000; // Default 30 seconds
            setInterval(() => {
                if (document.visibilityState === 'visible') {
                    htmx.trigger(element, 'refresh');
                }
            }, interval);
        });
    }

    // Search with debounce
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Setup search inputs with debouncing
    const searchInputs = document.querySelectorAll('input[hx-trigger*="keyup"]');
    searchInputs.forEach(input => {
        // Remove the default hx-trigger and setup custom debounced version
        const originalTrigger = input.getAttribute('hx-trigger');
        const url = input.getAttribute('hx-get') || input.getAttribute('hx-post');
        const target = input.getAttribute('hx-target');
        
        if (url && target) {
            input.removeAttribute('hx-trigger');
            
            const debouncedSearch = debounce(() => {
                const formData = new FormData();
                formData.append(input.name, input.value);
                
                // Get other form inputs in the same form
                const form = input.closest('form');
                if (form) {
                    const otherInputs = form.querySelectorAll('input, select');
                    otherInputs.forEach(otherInput => {
                        if (otherInput !== input && otherInput.name) {
                            formData.append(otherInput.name, otherInput.value);
                        }
                    });
                }
                
                fetch(url, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                        'HX-Request': 'true'
                    }
                })
                .then(response => response.text())
                .then(html => {
                    document.querySelector(target).innerHTML = html;
                    htmx.process(document.querySelector(target));
                });
            }, 300);
            
            input.addEventListener('keyup', debouncedSearch);
        }
    });

    // Initialize components
    setupAutoRefresh();

    // Notification system
    window.showNotification = function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button class="alert-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        const container = document.getElementById('messages') || document.createElement('div');
        if (!document.getElementById('messages')) {
            container.id = 'messages';
            container.className = 'messages-container';
            document.querySelector('.main-content').insertBefore(container, document.querySelector('.main-content').firstChild);
        }
        
        container.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
    };

    // Enhanced form handling
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        // Validate forms before sending
        if (evt.target.tagName === 'FORM') {
            const requiredFields = evt.target.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.classList.add('error');
                    isValid = false;
                } else {
                    field.classList.remove('error');
                }
            });
            
            if (!isValid) {
                evt.preventDefault();
                showNotification('Please fill in all required fields', 'error');
                return false;
            }
        }
    });

    // Handle HTMX errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        showNotification('Something went wrong. Please try again.', 'error');
    });

    document.body.addEventListener('htmx:timeout', function(evt) {
        showNotification('Request timed out. Please try again.', 'warning');
    });

    // Smooth scrolling for HTMX navigation
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        // Scroll to top of swapped content if it's a major page change
        if (evt.target.id === 'main-content' || evt.target.classList.contains('page-content')) {
            evt.target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    console.log('SimpExtrac HTMX Frontend initialized');
});

// Utility functions for HTMX interactions
window.SimpExtrac = {
    // Refresh a specific element
    refresh: function(selector) {
        const element = document.querySelector(selector);
        if (element && element.hasAttribute('hx-get')) {
            htmx.trigger(element, 'refresh');
        }
    },
    
    // Show/hide elements with animation
    show: function(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.style.display = 'block';
            element.style.opacity = '0';
            setTimeout(() => element.style.opacity = '1', 10);
        }
    },
    
    hide: function(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.style.opacity = '0';
            setTimeout(() => element.style.display = 'none', 300);
        }
    },
    
    // Toggle loading state
    setLoading: function(selector, isLoading) {
        const element = document.querySelector(selector);
        if (element) {
            if (isLoading) {
                element.classList.add('loading');
                element.disabled = true;
            } else {
                element.classList.remove('loading');
                element.disabled = false;
            }
        }
    }
};