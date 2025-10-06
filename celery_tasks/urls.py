"""
URL patterns for celery_tasks app
"""
from django.urls import path
from . import views

app_name = 'celery_tasks'

urlpatterns = [
    # Scheduled job management
    path('scheduled/', views.scheduled_jobs_list, name='scheduled_jobs'),
    path('scheduled/create/', views.create_scheduled_job, name='create_scheduled_job'),
    path('scheduled/<int:job_id>/toggle/', views.toggle_scheduled_job, name='toggle_scheduled_job'),
    path('runs/', views.job_runs_list, name='job_runs'),
    
    # API endpoints for Celery
    path('api/manual-scrape/', views.trigger_manual_scrape, name='trigger_manual_scrape'),
    path('api/job-status/<str:task_id>/', views.job_run_status, name='job_run_status'),
    path('api/dashboard-stats/', views.api_dashboard_stats, name='dashboard_stats'),
]