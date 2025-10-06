/**
 * Dashboard Charts JavaScript Module
 * Handles Chart.js initialization and chart configuration for dashboard visualizations
 */
(function() {
    'use strict';
    
    // Chart configuration constants
    const CHART_CONFIG = {
        CHART_HEIGHT: 200,
        COMPANIES_CHART_HEIGHT: 250,
        LOCATIONS_CHART_HEIGHT: 250,
        MAX_COMPANY_NAME_LENGTH: 20,
        CHART_ANIMATION_DURATION: 750
    };
    
    // Color palette for consistent styling
    const CHART_COLORS = {
        primary: '#3b82f6',
        secondary: '#6366f1', 
        success: '#10b981',
        warning: '#f59e0b',
        danger: '#ef4444',
        info: '#06b6d4',
        linkedin: '#0077b5',
        indeed: '#2557a7',
        glassdoor: '#0caa41'
    };
    
    // Charts state management
    const ChartsState = {
        sourcesChart: null,
        activityChart: null,
        companiesChart: null,
        locationsChart: null,
        isInitialized: false
    };
    
    // Dashboard Charts Module
    const DashboardCharts = {
        
        init(chartData) {
            console.log('Initializing Dashboard Charts module...');
            
            // Set Chart.js default configuration
            this.setupChartDefaults();
            
            // Initialize all charts with provided data
            this.initializeAllCharts(chartData);
            
            ChartsState.isInitialized = true;
            console.log('Dashboard Charts initialized successfully');
        },
        
        setupChartDefaults() {
            if (typeof Chart === 'undefined') {
                console.error('Chart.js not loaded');
                return;
            }
            
            Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
            Chart.defaults.font.size = 12;
            Chart.defaults.plugins.legend.display = true;
            Chart.defaults.plugins.legend.position = 'bottom';
            Chart.defaults.animation.duration = CHART_CONFIG.CHART_ANIMATION_DURATION;
            Chart.defaults.responsive = true;
            Chart.defaults.maintainAspectRatio = false;
            
            console.log('Chart.js defaults configured');
        },
        
        initializeAllCharts(data) {
            if (!data) {
                console.warn('No chart data provided');
                return;
            }
            
            // Initialize each chart type
            this.initializeSourcesChart(data.sources);
            this.initializeActivityChart(data.activity);
            this.initializeCompaniesChart(data.companies);
            this.initializeLocationsChart(data.locations);
        },
        
        // Sources Distribution Doughnut Chart
        initializeSourcesChart(sourcesData) {
            const canvas = document.getElementById('sourcesChart');
            if (!canvas || !sourcesData || sourcesData.length === 0) {
                console.warn('Sources chart: Canvas not found or no data');
                return;
            }
            
            try {
                ChartsState.sourcesChart = new Chart(canvas, {
                    type: 'doughnut',
                    data: {
                        labels: sourcesData.map(item => item.source || 'Unknown'),
                        datasets: [{
                            data: sourcesData.map(item => item.count),
                            backgroundColor: [
                                CHART_COLORS.indeed,
                                CHART_COLORS.glassdoor, 
                                CHART_COLORS.linkedin,
                                CHART_COLORS.primary,
                                CHART_COLORS.secondary
                            ],
                            borderWidth: 2,
                            borderColor: '#ffffff',
                            hoverBorderWidth: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    usePointStyle: true,
                                    font: {
                                        size: 11
                                    }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                        const percentage = ((context.parsed * 100) / total).toFixed(1);
                                        return `${context.label}: ${context.parsed} (${percentage}%)`;
                                    }
                                },
                                backgroundColor: '#1f2937',
                                titleColor: '#f9fafb',
                                bodyColor: '#f9fafb',
                                borderColor: CHART_COLORS.primary,
                                borderWidth: 1
                            }
                        }
                    }
                });
                
                console.log('Sources chart initialized');
            } catch (error) {
                console.error('Error initializing sources chart:', error);
            }
        },
        
        // Activity Line Chart (Last 7 Days)
        initializeActivityChart(activityData) {
            const canvas = document.getElementById('activityChart');
            if (!canvas || !activityData || activityData.length === 0) {
                console.warn('Activity chart: Canvas not found or no data');
                return;
            }
            
            try {
                ChartsState.activityChart = new Chart(canvas, {
                    type: 'line',
                    data: {
                        labels: activityData.map(item => item.date_label),
                        datasets: [{
                            label: 'Jobs Scraped',
                            data: activityData.map(item => item.count),
                            borderColor: CHART_COLORS.primary,
                            backgroundColor: CHART_COLORS.primary + '20',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointBackgroundColor: CHART_COLORS.primary,
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            pointRadius: 5,
                            pointHoverRadius: 7
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1,
                                    font: {
                                        size: 11
                                    }
                                },
                                grid: {
                                    color: '#f1f5f9',
                                    lineWidth: 1
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    font: {
                                        size: 11
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                backgroundColor: '#1f2937',
                                titleColor: '#f9fafb',
                                bodyColor: '#f9fafb',
                                borderColor: CHART_COLORS.primary,
                                borderWidth: 1
                            }
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index'
                        }
                    }
                });
                
                console.log('Activity chart initialized');
            } catch (error) {
                console.error('Error initializing activity chart:', error);
            }
        },
        
        // Top Companies Horizontal Bar Chart
        initializeCompaniesChart(companiesData) {
            const canvas = document.getElementById('companiesChart');
            if (!canvas || !companiesData || companiesData.length === 0) {
                console.warn('Companies chart: Canvas not found or no data');
                return;
            }
            
            try {
                ChartsState.companiesChart = new Chart(canvas, {
                    type: 'bar',
                    data: {
                        labels: companiesData.map(item => {
                            const name = item.company__name || 'Unknown';
                            return name.length > CHART_CONFIG.MAX_COMPANY_NAME_LENGTH 
                                ? name.substring(0, CHART_CONFIG.MAX_COMPANY_NAME_LENGTH) + '...' 
                                : name;
                        }),
                        datasets: [{
                            label: 'Jobs',
                            data: companiesData.map(item => item.count),
                            backgroundColor: CHART_COLORS.success + '80',
                            borderColor: CHART_COLORS.success,
                            borderWidth: 1,
                            borderRadius: 4,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1,
                                    font: {
                                        size: 11
                                    }
                                },
                                grid: {
                                    color: '#f1f5f9'
                                }
                            },
                            y: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    font: {
                                        size: 10
                                    }
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                backgroundColor: '#1f2937',
                                titleColor: '#f9fafb',
                                bodyColor: '#f9fafb',
                                callbacks: {
                                    title: function(context) {
                                        // Show full company name in tooltip
                                        const index = context[0].dataIndex;
                                        return companiesData[index].company__name || 'Unknown';
                                    }
                                }
                            }
                        }
                    }
                });
                
                console.log('Companies chart initialized');
            } catch (error) {
                console.error('Error initializing companies chart:', error);
            }
        },
        
        // Locations Polar Area Chart
        initializeLocationsChart(locationsData) {
            const canvas = document.getElementById('locationsChart');
            if (!canvas || !locationsData || locationsData.length === 0) {
                console.warn('Locations chart: Canvas not found or no data');
                return;
            }
            
            try {
                ChartsState.locationsChart = new Chart(canvas, {
                    type: 'polarArea',
                    data: {
                        labels: locationsData.map(item => item.location || 'Remote'),
                        datasets: [{
                            data: locationsData.map(item => item.count),
                            backgroundColor: [
                                CHART_COLORS.primary + '80',
                                CHART_COLORS.secondary + '80',
                                CHART_COLORS.success + '80',
                                CHART_COLORS.warning + '80',
                                CHART_COLORS.danger + '80',
                                CHART_COLORS.info + '80',
                                CHART_COLORS.linkedin + '80',
                                CHART_COLORS.glassdoor + '80'
                            ],
                            borderColor: [
                                CHART_COLORS.primary,
                                CHART_COLORS.secondary,
                                CHART_COLORS.success,
                                CHART_COLORS.warning,
                                CHART_COLORS.danger,
                                CHART_COLORS.info,
                                CHART_COLORS.linkedin,
                                CHART_COLORS.glassdoor
                            ],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 10,
                                    usePointStyle: true,
                                    font: {
                                        size: 10
                                    }
                                }
                            },
                            tooltip: {
                                backgroundColor: '#1f2937',
                                titleColor: '#f9fafb',
                                bodyColor: '#f9fafb'
                            }
                        },
                        scales: {
                            r: {
                                beginAtZero: true,
                                ticks: {
                                    stepSize: 1,
                                    backdropColor: 'transparent',
                                    font: {
                                        size: 10
                                    }
                                },
                                grid: {
                                    color: '#f1f5f9'
                                }
                            }
                        }
                    }
                });
                
                console.log('Locations chart initialized');
            } catch (error) {
                console.error('Error initializing locations chart:', error);
            }
        },
        
        // Update charts with new data
        updateCharts(newData) {
            if (!ChartsState.isInitialized) {
                console.warn('Charts not initialized, cannot update');
                return;
            }
            
            try {
                if (newData.sources && ChartsState.sourcesChart) {
                    this.updateSourcesChart(newData.sources);
                }
                
                if (newData.activity && ChartsState.activityChart) {
                    this.updateActivityChart(newData.activity);
                }
                
                if (newData.companies && ChartsState.companiesChart) {
                    this.updateCompaniesChart(newData.companies);
                }
                
                if (newData.locations && ChartsState.locationsChart) {
                    this.updateLocationsChart(newData.locations);
                }
                
                console.log('Charts updated with new data');
            } catch (error) {
                console.error('Error updating charts:', error);
            }
        },
        
        updateSourcesChart(sourcesData) {
            const chart = ChartsState.sourcesChart;
            chart.data.labels = sourcesData.map(item => item.source || 'Unknown');
            chart.data.datasets[0].data = sourcesData.map(item => item.count);
            chart.update();
        },
        
        updateActivityChart(activityData) {
            const chart = ChartsState.activityChart;
            chart.data.labels = activityData.map(item => item.date_label);
            chart.data.datasets[0].data = activityData.map(item => item.count);
            chart.update();
        },
        
        updateCompaniesChart(companiesData) {
            const chart = ChartsState.companiesChart;
            chart.data.labels = companiesData.map(item => {
                const name = item.company__name || 'Unknown';
                return name.length > CHART_CONFIG.MAX_COMPANY_NAME_LENGTH 
                    ? name.substring(0, CHART_CONFIG.MAX_COMPANY_NAME_LENGTH) + '...' 
                    : name;
            });
            chart.data.datasets[0].data = companiesData.map(item => item.count);
            chart.update();
        },
        
        updateLocationsChart(locationsData) {
            const chart = ChartsState.locationsChart;
            chart.data.labels = locationsData.map(item => item.location || 'Remote');
            chart.data.datasets[0].data = locationsData.map(item => item.count);
            chart.update();
        },
        
        // Destroy all charts (cleanup)
        destroyCharts() {
            Object.values(ChartsState).forEach(chart => {
                if (chart && typeof chart.destroy === 'function') {
                    chart.destroy();
                }
            });
            
            ChartsState.sourcesChart = null;
            ChartsState.activityChart = null;
            ChartsState.companiesChart = null;
            ChartsState.locationsChart = null;
            ChartsState.isInitialized = false;
            
            console.log('All charts destroyed');
        },
        
        // Resize all charts
        resizeCharts() {
            Object.values(ChartsState).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        }
    };
    
    // Helper function to initialize charts from template data
    window.initializeDashboardCharts = function(chartData) {
        // Parse JSON data if it's a string
        const parsedData = {
            sources: typeof chartData.sources === 'string' ? JSON.parse(chartData.sources) : chartData.sources,
            activity: typeof chartData.activity === 'string' ? JSON.parse(chartData.activity) : chartData.activity,
            companies: typeof chartData.companies === 'string' ? JSON.parse(chartData.companies) : chartData.companies,
            locations: typeof chartData.locations === 'string' ? JSON.parse(chartData.locations) : chartData.locations
        };
        
        DashboardCharts.init(parsedData);
    };
    
    // Expose DashboardCharts to global scope
    window.SimpExtrac = window.SimpExtrac || {};
    window.SimpExtrac.DashboardCharts = DashboardCharts;
    
    // Handle window resize
    window.addEventListener('resize', () => {
        if (ChartsState.isInitialized) {
            DashboardCharts.resizeCharts();
        }
    });
    
})();