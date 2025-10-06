// Dashboard-specific JavaScript module
(function() {
    'use strict';
    
    // Configuration constants
    const DASHBOARD_CONFIG = {
        STATS_REFRESH_INTERVAL: 30000,    // 30 seconds
        JOBS_REFRESH_INTERVAL: 60000,     // 60 seconds
        SEARCH_DEBOUNCE_DELAY: 300,       // 300ms
        MAX_RETRY_ATTEMPTS: 3,
        RETRY_DELAY: 1000                 // 1 second
    };
    
    // Dashboard state management
    const DashboardState = {
        intervals: new Map(),
        retryAttempts: new Map(),
        isVisible: true,
        autoRefreshEnabled: true
    };
    
    // Dashboard module
    const Dashboard = {
        
        init() {
            console.log('Initializing Dashboard module...');
            this.setupAutoRefreshToggle();
            this.setupAutoRefresh();
            this.setupSearchHandlers();
            this.setupModalHandlers();
            this.setupVisibilityHandling();
            this.setupErrorHandling();
            console.log('Dashboard initialized successfully');
        },
        
        // Auto-refresh toggle functionality
        setupAutoRefreshToggle() {
            const toggle = document.getElementById('auto-refresh-toggle');
            const refreshStatus = document.getElementById('refresh-status');
            
            if (!toggle || !refreshStatus) return;
            
            // Initialize state from localStorage
            const savedState = localStorage.getItem('dashboard-auto-refresh');
            if (savedState !== null) {
                DashboardState.autoRefreshEnabled = JSON.parse(savedState);
                toggle.checked = DashboardState.autoRefreshEnabled;
            }
            
            this.updateRefreshStatus();
            
            // Handle toggle changes
            toggle.addEventListener('change', (e) => {
                DashboardState.autoRefreshEnabled = e.target.checked;
                localStorage.setItem('dashboard-auto-refresh', JSON.stringify(DashboardState.autoRefreshEnabled));
                
                this.updateRefreshStatus();
                
                if (DashboardState.autoRefreshEnabled) {
                    this.resumeAutoRefresh();
                    window.showNotification('Auto-refresh enabled', 'success');
                } else {
                    this.pauseAutoRefresh();
                    window.showNotification('Auto-refresh disabled', 'info');
                }
            });
        },
        
        updateRefreshStatus() {
            const refreshStatus = document.getElementById('refresh-status');
            if (!refreshStatus) return;
            
            if (DashboardState.autoRefreshEnabled) {
                refreshStatus.innerHTML = '<i class="fas fa-sync-alt"></i> Active';
                refreshStatus.classList.remove('disabled');
            } else {
                refreshStatus.innerHTML = '<i class="fas fa-pause"></i> Paused';
                refreshStatus.classList.add('disabled');
            }
        },
        
        pauseAutoRefresh() {
            // Pause all intervals but don't clear them
            DashboardState.intervals.forEach((intervalId, key) => {
                clearInterval(intervalId);
                console.log(`Auto-refresh paused for ${key}`);
            });
            
            // Hide refresh indicators
            document.querySelectorAll('.auto-refresh-indicator').forEach(indicator => {
                indicator.style.opacity = '0.3';
            });
        },
        
        resumeAutoRefresh() {
            // Resume auto-refresh for all elements
            const statsElement = document.querySelector('[data-auto-refresh]');
            if (statsElement) {
                const interval = parseInt(statsElement.dataset.autoRefresh) || DASHBOARD_CONFIG.STATS_REFRESH_INTERVAL;
                this.startAutoRefresh('stats', statsElement, interval);
            }
            
            const jobsElement = document.querySelector('#recent-jobs-list');
            if (jobsElement) {
                this.startAutoRefresh('jobs', jobsElement, DASHBOARD_CONFIG.JOBS_REFRESH_INTERVAL);
            }
            
            // Show refresh indicators
            document.querySelectorAll('.auto-refresh-indicator').forEach(indicator => {
                indicator.style.opacity = '1';
            });
        },
        
        // Auto-refresh functionality with error handling
        setupAutoRefresh() {
            // Only setup auto-refresh if enabled
            if (!DashboardState.autoRefreshEnabled) return;
            
            // Stats auto-refresh
            const statsElement = document.querySelector('[data-auto-refresh]');
            if (statsElement) {
                const interval = parseInt(statsElement.dataset.autoRefresh) || DASHBOARD_CONFIG.STATS_REFRESH_INTERVAL;
                this.startAutoRefresh('stats', statsElement, interval);
            }
            
            // Recent jobs auto-refresh
            const jobsElement = document.querySelector('#recent-jobs-list');
            if (jobsElement) {
                this.startAutoRefresh('jobs', jobsElement, DASHBOARD_CONFIG.JOBS_REFRESH_INTERVAL);
            }
        },
        
        startAutoRefresh(key, element, interval) {
            // Clear existing interval if any
            this.stopAutoRefresh(key);
            
            const refreshFunction = () => {
                if (DashboardState.isVisible && DashboardState.autoRefreshEnabled && document.contains(element)) {
                    this.refreshElement(element, key);
                }
            };
            
            // Start interval
            const intervalId = setInterval(refreshFunction, interval);
            DashboardState.intervals.set(key, intervalId);
            
            console.log(`Auto-refresh started for ${key} (${interval}ms interval)`);
        },
        
        stopAutoRefresh(key) {
            if (DashboardState.intervals.has(key)) {
                clearInterval(DashboardState.intervals.get(key));
                DashboardState.intervals.delete(key);
                console.log(`Auto-refresh stopped for ${key}`);
            }
        },
        
        async refreshElement(element, key) {
            const url = element.getAttribute('hx-get');
            if (!url) return;
            
            try {
                // Add loading state
                this.setLoadingState(element, true);
                
                // Show refresh indicator
                this.showRefreshIndicator(key);
                
                // Trigger HTMX refresh
                htmx.trigger(element, 'refresh');
                
            } catch (error) {
                this.handleRefreshError(key, error);
            }
        },
        
        setLoadingState(element, isLoading) {
            if (isLoading) {
                element.classList.add('dashboard-loading');
                
                // Add shimmer effect to stats
                if (element.classList.contains('stats-grid')) {
                    element.classList.add('stats-loading');
                }
            } else {
                element.classList.remove('dashboard-loading', 'stats-loading');
            }
        },
        
        showRefreshIndicator(key) {
            const indicator = document.querySelector(`[data-refresh-indicator="${key}"]`);
            if (indicator) {
                indicator.classList.add('refreshing');
                setTimeout(() => {
                    indicator.classList.remove('refreshing');
                }, 2000);
            }
        },
        
        handleRefreshError(key, error) {
            console.error(`Refresh error for ${key}:`, error);
            
            // Increment retry attempts
            const attempts = DashboardState.retryAttempts.get(key) || 0;
            DashboardState.retryAttempts.set(key, attempts + 1);
            
            // Show user-friendly error message
            if (attempts < DASHBOARD_CONFIG.MAX_RETRY_ATTEMPTS) {
                window.showNotification(`Refresh failed, retrying... (${attempts + 1}/${DASHBOARD_CONFIG.MAX_RETRY_ATTEMPTS})`, 'warning');
                
                // Retry after delay
                setTimeout(() => {
                    const element = document.querySelector(`[data-refresh-key="${key}"]`);
                    if (element) {
                        this.refreshElement(element, key);
                    }
                }, DASHBOARD_CONFIG.RETRY_DELAY * (attempts + 1));
            } else {
                window.showNotification('Auto-refresh temporarily disabled due to errors', 'error');
                this.stopAutoRefresh(key);
                DashboardState.retryAttempts.delete(key);
            }
        },
        
        // Enhanced search with debouncing and error handling
        setupSearchHandlers() {
            const searchForm = document.querySelector('.search-form');
            if (!searchForm) return;
            
            const searchInput = searchForm.querySelector('input[name="search"]');
            if (!searchInput) return;
            
            // Create debounced search function
            const debouncedSearch = this.debounce((value) => {
                this.performSearch(searchForm, value);
            }, DASHBOARD_CONFIG.SEARCH_DEBOUNCE_DELAY);
            
            // Setup search input handler
            searchInput.addEventListener('input', (e) => {
                const value = e.target.value.trim();
                if (value.length >= 2 || value.length === 0) {
                    debouncedSearch(value);
                }
            });
            
            // Setup form submission
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.performSearch(searchForm, searchInput.value.trim());
            });
        },
        
        async performSearch(form, query) {
            const resultsContainer = document.querySelector('#search-results');
            if (!resultsContainer) return;
            
            try {
                // Show loading state
                resultsContainer.innerHTML = '<div class="spinner"></div><p>Searching...</p>';
                
                // Prepare form data
                const formData = new FormData(form);
                
                // Make search request
                const response = await fetch(form.action || window.location.pathname, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
                        'HX-Request': 'true'
                    }
                });
                
                if (response.ok) {
                    const html = await response.text();
                    resultsContainer.innerHTML = html;
                    htmx.process(resultsContainer);
                } else {
                    throw new Error(`Search failed: ${response.status}`);
                }
                
            } catch (error) {
                console.error('Search error:', error);
                resultsContainer.innerHTML = '<p class="text-center text-secondary">Search failed. Please try again.</p>';
                window.showNotification('Search failed. Please try again.', 'error');
            }
        },
        
        // Modal handling
        setupModalHandlers() {
            // Job detail modal
            const modal = document.querySelector('#job-detail-modal');
            if (!modal) return;
            
            // Close modal on backdrop click
            const backdrop = modal.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.addEventListener('click', () => {
                    this.hideModal(modal);
                });
            }
            
            // Close modal on Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                    this.hideModal(modal);
                }
            });
        },
        
        showModal(modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            
            // Focus trap for accessibility
            const focusableElements = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (focusableElements.length > 0) {
                focusableElements[0].focus();
            }
        },
        
        hideModal(modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        },
        
        // Visibility handling for performance
        setupVisibilityHandling() {
            document.addEventListener('visibilitychange', () => {
                DashboardState.isVisible = !document.hidden;
                
                if (DashboardState.isVisible) {
                    console.log('Dashboard visible - resuming auto-refresh');
                    // Reset retry attempts when page becomes visible
                    DashboardState.retryAttempts.clear();
                } else {
                    console.log('Dashboard hidden - pausing auto-refresh');
                }
            });
        },
        
        // Enhanced error handling
        setupErrorHandling() {
            // HTMX error handling
            document.body.addEventListener('htmx:responseError', (evt) => {
                console.error('HTMX Response Error:', evt.detail);
                this.handleHTMXError(evt);
            });
            
            document.body.addEventListener('htmx:timeout', (evt) => {
                console.warn('HTMX Timeout:', evt.detail);
                window.showNotification('Request timed out. Please try again.', 'warning');
            });
            
            document.body.addEventListener('htmx:afterRequest', (evt) => {
                // Remove loading states after successful requests
                const target = evt.target;
                this.setLoadingState(target, false);
            });
        },
        
        handleHTMXError(evt) {
            const status = evt.detail.xhr?.status;
            let message = 'Something went wrong. Please try again.';
            
            switch (status) {
                case 403:
                    message = 'Access denied. Please refresh the page.';
                    break;
                case 404:
                    message = 'Requested resource not found.';
                    break;
                case 500:
                    message = 'Server error. Please try again later.';
                    break;
                case 0:
                    message = 'Network error. Please check your connection.';
                    break;
            }
            
            window.showNotification(message, 'error');
        },
        
        // Manual refresh function
        manualRefresh(selector) {
            const element = document.querySelector(selector);
            if (element) {
                const key = element.dataset.refreshKey || 'manual';
                this.refreshElement(element, key);
            }
        },
        
        // Manual refresh all dashboard components
        manualRefreshAll() {
            console.log('Manual refresh triggered for all components');
            
            // Refresh stats
            const statsElement = document.querySelector('[data-refresh-key="stats"]');
            if (statsElement) {
                this.refreshElement(statsElement, 'stats');
            }
            
            // Refresh recent jobs
            const jobsElement = document.querySelector('#recent-jobs-list');
            if (jobsElement) {
                this.refreshElement(jobsElement, 'jobs');
            }
            
            window.showNotification('Dashboard refreshed', 'success');
        },
        
        // Cleanup function
        cleanup() {
            console.log('Cleaning up Dashboard module...');
            
            // Clear all intervals
            DashboardState.intervals.forEach((intervalId, key) => {
                clearInterval(intervalId);
                console.log(`Cleared interval for ${key}`);
            });
            
            DashboardState.intervals.clear();
            DashboardState.retryAttempts.clear();
            
            // Restore body overflow
            document.body.style.overflow = '';
        },
        
        // Utility functions
        debounce(func, wait) {
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
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => Dashboard.init());
    } else {
        Dashboard.init();
    }
    
    // Cleanup when page unloads
    window.addEventListener('beforeunload', () => Dashboard.cleanup());
    
    // Expose Dashboard to global scope for external access
    window.SimpExtrac = window.SimpExtrac || {};
    window.SimpExtrac.Dashboard = Dashboard;
    
})();