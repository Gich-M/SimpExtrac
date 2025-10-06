/**
 * Scraper Control JavaScript Module
 * Handles form validation, scheduling options, and scraping session management
 */
(function() {
    'use strict';
    
    // Configuration constants
    const SCRAPER_CONFIG = {
        SCRAPING_UPDATE_INTERVAL: 1000,  // 1 second
        MIN_CUSTOM_MINUTES: 1,
        MAX_CUSTOM_MINUTES: 1440,        // 24 hours
        MIN_JOB_TITLE_LENGTH: 1
    };
    
    // Scraper state management
    const ScraperState = {
        scrapingStartTime: null,
        elapsedTimeInterval: null,
        isScrapingActive: false
    };
    
    // Scraper Control Module
    const ScraperControl = {
        
        init() {
            console.log('Initializing Scraper Control module...');
            this.setupFormValidation();
            this.setupScheduleOptions();
            this.setupHTMXEventHandlers();
            this.initializeScheduleForm();
            console.log('Scraper Control initialized successfully');
        },
        
        // Enhanced form validation for manual scraping
        setupFormValidation() {
            const scraperForm = document.querySelector('.scraper-form');
            if (!scraperForm) return;
            
            scraperForm.addEventListener('submit', (e) => {
                if (!this.validateScrapingForm(e)) {
                    return false;
                }
                
                // Start the loading experience
                this.initializeScrapingSession();
            });
            
            console.log('Scraping form validation setup complete');
        },
        
        validateScrapingForm(event) {
            const jobTitle = document.getElementById('job_title')?.value.trim();
            const checkedSources = document.querySelectorAll('input[name="sources"]:checked');
            
            // Validate job title
            if (!jobTitle || jobTitle.length < SCRAPER_CONFIG.MIN_JOB_TITLE_LENGTH) {
                event.preventDefault();
                window.showNotification('Please enter a valid job title', 'error');
                return false;
            }
            
            // Validate sources selection
            if (checkedSources.length === 0) {
                event.preventDefault();
                window.showNotification('Please select at least one source', 'error');
                return false;
            }
            
            return true;
        },
        
        // Schedule form validation and setup
        setupScheduleOptions() {
            const scheduleForm = document.querySelector('.schedule-form');
            if (!scheduleForm) return;
            
            // Setup form submission validation
            scheduleForm.addEventListener('submit', (e) => {
                if (!this.validateScheduleForm(e)) {
                    return false;
                }
            });
            
            // Setup interval change handler
            const intervalSelect = document.getElementById('schedule_interval');
            if (intervalSelect) {
                intervalSelect.addEventListener('change', () => {
                    this.toggleScheduleOptions();
                });
            }
            
            console.log('Schedule form setup complete');
        },
        
        validateScheduleForm(event) {
            const jobTitle = document.getElementById('schedule_job_title')?.value.trim();
            const interval = document.getElementById('schedule_interval')?.value;
            
            // Validate job title
            if (!jobTitle || jobTitle.length < SCRAPER_CONFIG.MIN_JOB_TITLE_LENGTH) {
                event.preventDefault();
                window.showNotification('Please enter a job title for scheduling', 'error');
                return false;
            }
            
            // Validate custom interval
            if (interval === 'custom') {
                const customMinutes = document.getElementById('custom_minutes')?.value;
                const minutes = parseInt(customMinutes);
                
                if (!customMinutes || isNaN(minutes) || 
                    minutes < SCRAPER_CONFIG.MIN_CUSTOM_MINUTES || 
                    minutes > SCRAPER_CONFIG.MAX_CUSTOM_MINUTES) {
                    event.preventDefault();
                    window.showNotification(
                        `Please enter a valid interval (${SCRAPER_CONFIG.MIN_CUSTOM_MINUTES}-${SCRAPER_CONFIG.MAX_CUSTOM_MINUTES} minutes)`, 
                        'error'
                    );
                    return false;
                }
            }
            
            // Validate one-time scheduling
            if (interval === 'once') {
                if (!this.validateOneTimeSchedule(event)) {
                    return false;
                }
            }
            
            // Validate weekly options
            if (interval === 'weekly') {
                const checkedDays = document.querySelectorAll('input[name="days_of_week"]:checked');
                if (checkedDays.length === 0) {
                    event.preventDefault();
                    window.showNotification('Please select at least one day of the week', 'error');
                    return false;
                }
            }
            
            // Validate sources selection
            const checkedSources = document.querySelectorAll('input[name="schedule_sources"]:checked');
            if (checkedSources.length === 0) {
                event.preventDefault();
                window.showNotification('Please select at least one source for scheduled scraping', 'error');
                return false;
            }
            
            return true;
        },
        
        validateOneTimeSchedule(event) {
            const scheduleDate = document.getElementById('schedule_date')?.value;
            const scheduleTime = document.getElementById('schedule_time')?.value || '09:00';
            
            if (!scheduleDate) {
                event.preventDefault();
                window.showNotification('Please select a date for one-time scheduling', 'error');
                return false;
            }
            
            // Check if selected datetime is in the future
            const selectedDateTime = new Date(scheduleDate + 'T' + scheduleTime);
            if (selectedDateTime <= new Date()) {
                event.preventDefault();
                window.showNotification('Please select a future date and time', 'error');
                return false;
            }
            
            return true;
        },
        
        // Toggle schedule options based on interval selection
        toggleScheduleOptions() {
            const interval = document.getElementById('schedule_interval')?.value;
            
            const optionElements = {
                custom: document.getElementById('custom-options'),
                time: document.getElementById('time-options'),
                date: document.getElementById('date-options'),
                weekly: document.getElementById('weekly-options'),
                monthly: document.getElementById('monthly-options')
            };
            
            // Hide all options first
            Object.values(optionElements).forEach(element => {
                if (element) {
                    element.style.display = 'none';
                }
            });
            
            // Show relevant options based on interval
            switch (interval) {
                case 'custom':
                    this.showElement(optionElements.custom);
                    this.hideElement(optionElements.time);
                    break;
                    
                case 'once':
                    this.showElement(optionElements.date);
                    this.showElement(optionElements.time);
                    this.setMinimumDate();
                    break;
                    
                case 'weekly':
                    this.showElement(optionElements.weekly);
                    this.showElement(optionElements.time);
                    break;
                    
                case 'monthly':
                    this.showElement(optionElements.monthly);
                    this.showElement(optionElements.time);
                    break;
                    
                case '30min':
                case 'hourly':
                    this.showElement(optionElements.time);
                    break;
                    
                default:
                    this.showElement(optionElements.time);
                    break;
            }
            
            console.log(`Schedule options updated for interval: ${interval}`);
        },
        
        showElement(element) {
            if (element) {
                element.style.display = 'block';
            }
        },
        
        hideElement(element) {
            if (element) {
                element.style.display = 'none';
            }
        },
        
        setMinimumDate() {
            const dateInput = document.getElementById('schedule_date');
            if (dateInput) {
                const today = new Date().toISOString().split('T')[0];
                dateInput.setAttribute('min', today);
            }
        },
        
        // Scraping session management
        initializeScrapingSession() {
            ScraperState.scrapingStartTime = Date.now();
            ScraperState.isScrapingActive = true;
            
            // Reset live stats
            this.updateLiveStats(0, '0s');
            
            // Start elapsed time counter
            ScraperState.elapsedTimeInterval = setInterval(() => {
                this.updateElapsedTime();
            }, SCRAPER_CONFIG.SCRAPING_UPDATE_INTERVAL);
            
            // Update scraping button state
            this.updateScrapingButtonState(true);
            
            console.log('Scraping session initialized');
        },
        
        updateLiveStats(jobsFound, elapsedTime) {
            const jobsElement = document.getElementById('live-jobs-found');
            const timeElement = document.getElementById('live-elapsed-time');
            
            if (jobsElement) jobsElement.textContent = jobsFound.toString();
            if (timeElement) timeElement.textContent = elapsedTime;
        },
        
        updateElapsedTime() {
            if (!ScraperState.scrapingStartTime) return;
            
            const elapsed = Math.floor((Date.now() - ScraperState.scrapingStartTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            
            const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
            
            const timeElement = document.getElementById('live-elapsed-time');
            if (timeElement) {
                timeElement.textContent = timeStr;
            }
        },
        
        updateScrapingButtonState(isScrapingActive) {
            const scraperForm = document.querySelector('.scraper-form');
            if (!scraperForm) return;
            
            const submitBtn = scraperForm.querySelector('button[type="submit"]');
            if (!submitBtn) return;
            
            if (isScrapingActive) {
                submitBtn.disabled = true;
                submitBtn.dataset.originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
            } else {
                submitBtn.disabled = false;
                if (submitBtn.dataset.originalText) {
                    submitBtn.innerHTML = submitBtn.dataset.originalText;
                    delete submitBtn.dataset.originalText;
                } else {
                    submitBtn.innerHTML = '<i class="fas fa-play"></i> Start Manual Scan';
                }
            }
        },
        
        resetScrapingSession() {
            // Clear elapsed time interval
            if (ScraperState.elapsedTimeInterval) {
                clearInterval(ScraperState.elapsedTimeInterval);
                ScraperState.elapsedTimeInterval = null;
            }
            
            // Reset button state
            this.updateScrapingButtonState(false);
            
            // Reset state
            ScraperState.scrapingStartTime = null;
            ScraperState.isScrapingActive = false;
            
            console.log('Scraping session reset');
        },
        
        // HTMX event handlers
        setupHTMXEventHandlers() {
            // Handle scraping start
            document.body.addEventListener('htmx:beforeRequest', (evt) => {
                if (evt.detail.target.id === 'scraper-results') {
                    this.showScrapingLoader();
                }
            });
            
            // Handle scraping completion
            document.body.addEventListener('htmx:afterRequest', (evt) => {
                if (evt.detail.target.id === 'scraper-results') {
                    this.handleScrapingCompletion(evt);
                }
            });
            
            // Handle scraping errors
            document.body.addEventListener('htmx:responseError', (evt) => {
                if (evt.detail.target.id === 'scraper-results') {
                    this.handleScrapingError();
                }
            });
            
            console.log('HTMX event handlers setup complete');
        },
        
        showScrapingLoader() {
            const loadingDiv = document.getElementById('scraper-loading');
            if (loadingDiv) {
                loadingDiv.classList.remove('hidden');
            }
        },
        
        hideScrapingLoader() {
            const loadingDiv = document.getElementById('scraper-loading');
            if (loadingDiv) {
                loadingDiv.classList.add('hidden');
            }
        },
        
        handleScrapingCompletion(evt) {
            setTimeout(() => {
                this.hideScrapingLoader();
                this.resetScrapingSession();
                
                if (evt.detail.xhr.status === 200) {
                    window.showNotification('Scraping completed!', 'success');
                }
            }, 500);
        },
        
        handleScrapingError() {
            this.hideScrapingLoader();
            this.resetScrapingSession();
            window.showNotification('Scraping failed. Please try again.', 'error');
        },
        
        // Initialize form on page load
        initializeScheduleForm() {
            // Set up initial state
            this.toggleScheduleOptions();
            
            console.log('Schedule form initialized');
        },
        
        // Public API for manual control
        manualStartScraping() {
            const scraperForm = document.querySelector('.scraper-form');
            if (scraperForm && !ScraperState.isScrapingActive) {
                scraperForm.dispatchEvent(new Event('submit'));
            }
        },
        
        manualStopScraping() {
            if (ScraperState.isScrapingActive) {
                this.resetScrapingSession();
                window.showNotification('Scraping stopped', 'info');
            }
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ScraperControl.init());
    } else {
        ScraperControl.init();
    }
    
    // Expose ScraperControl to global scope
    window.SimpExtrac = window.SimpExtrac || {};
    window.SimpExtrac.ScraperControl = ScraperControl;
    
    // Global function for schedule options (backward compatibility)
    window.toggleScheduleOptions = function() {
        ScraperControl.toggleScheduleOptions();
    };
    
})();