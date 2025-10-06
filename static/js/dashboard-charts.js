// Dashboard Charts Initialization Function
function initializeDashboardCharts(chartData) {
    console.log('Initializing dashboard charts with data:', chartData);
    
    // Chart.js default configuration
    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    Chart.defaults.font.size = 12;
    Chart.defaults.plugins.legend.display = true;
    Chart.defaults.plugins.legend.position = 'bottom';
    
    // Color palette for consistent styling
    const colors = {
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
    
    // Sources Distribution Pie Chart
    const sourcesData = chartData.sources;
    if (sourcesData && sourcesData.length > 0) {
        const sourcesChart = new Chart(document.getElementById('sourcesChart'), {
            type: 'doughnut',
            data: {
                labels: sourcesData.map(item => item.source || 'Unknown'),
                datasets: [{
                    data: sourcesData.map(item => item.count),
                    backgroundColor: [
                        colors.indeed,
                        colors.glassdoor, 
                        colors.linkedin,
                        colors.primary,
                        colors.secondary
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
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
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed * 100) / total).toFixed(1);
                                return `${context.label}: ${context.parsed} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Activity Line Chart (Last 7 Days)
    const activityData = chartData.activity;
    if (activityData && activityData.length > 0) {
        const activityChart = new Chart(document.getElementById('activityChart'), {
            type: 'line',
            data: {
                labels: activityData.map(item => item.date_label),
                datasets: [{
                    label: 'Jobs Scraped',
                    data: activityData.map(item => item.count),
                    borderColor: colors.primary,
                    backgroundColor: colors.primary + '20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: colors.primary,
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        },
                        grid: {
                            color: '#f1f5f9'
                        }
                    },
                    x: {
                        grid: {
                            display: false
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
                        borderColor: colors.primary,
                        borderWidth: 1
                    }
                }
            }
        });
    }
    
    // Top Companies Horizontal Bar Chart
    const companiesData = chartData.companies;
    if (companiesData && companiesData.length > 0) {
        const companiesChart = new Chart(document.getElementById('companiesChart'), {
            type: 'bar',
            data: {
                labels: companiesData.map(item => {
                    const name = item.company__name || 'Unknown';
                    return name.length > 20 ? name.substring(0, 20) + '...' : name;
                }),
                datasets: [{
                    label: 'Jobs',
                    data: companiesData.map(item => item.count),
                    backgroundColor: colors.success + '80',
                    borderColor: colors.success,
                    borderWidth: 1,
                    borderRadius: 4
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
                            stepSize: 1
                        },
                        grid: {
                            color: '#f1f5f9'
                        }
                    },
                    y: {
                        grid: {
                            display: false
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
                        bodyColor: '#f9fafb'
                    }
                }
            }
        });
    }
    
    // Locations Polar Area Chart
    const locationsData = chartData.locations;
    if (locationsData && locationsData.length > 0) {
        const locationsChart = new Chart(document.getElementById('locationsChart'), {
            type: 'polarArea',
            data: {
                labels: locationsData.map(item => item.location || 'Remote'),
                datasets: [{
                    data: locationsData.map(item => item.count),
                    backgroundColor: [
                        colors.primary + '80',
                        colors.secondary + '80',
                        colors.success + '80',
                        colors.warning + '80',
                        colors.danger + '80',
                        colors.info + '80',
                        colors.linkedin + '80',
                        colors.glassdoor + '80'
                    ],
                    borderColor: [
                        colors.primary,
                        colors.secondary,
                        colors.success,
                        colors.warning,
                        colors.danger,
                        colors.info,
                        colors.linkedin,
                        colors.glassdoor
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
                                size: 11
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
                            backdropColor: 'transparent'
                        },
                        grid: {
                            color: '#f1f5f9'
                        }
                    }
                }
            }
        });
    }
}