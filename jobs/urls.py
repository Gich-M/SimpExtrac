from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from .views import CompanyViewSet, JobViewSet

@api_view(['GET'])
def api_root(request, format=None):
    """
    SimpExtrac API Root - Complete Backend API Documentation
    
    A comprehensive job scraping platform built with Django + Celery + Redis
    demonstrating modern backend architecture and RESTful API design.
    """
    base_url = request.build_absolute_uri('/')
    
    return Response({
        "message": "SimpExtrac Job Scraping Platform API",
        "version": "1.0",
        "documentation": {
            "description": "Full-stack job scraping platform with scheduled tasks, real-time updates, and comprehensive data management",
            "tech_stack": ["Django 5.2.7", "Django REST Framework", "Celery", "Redis", "HTMX", "Selenium"]
        },
        
        # Core Data Endpoints
        "data_endpoints": {
            "companies": reverse('company-list', request=request, format=format),
            "jobs": reverse('job-list', request=request, format=format),
            "job_statistics": f"{base_url}api/jobs/stats/",
            "company_jobs": f"{base_url}api/companies/{{id}}/jobs/"
        },
        
        # Task Management & Automation
        "automation_endpoints": {
            "manual_scraping": f"{base_url}celery/api/manual-scrape/",
            "task_status": f"{base_url}celery/api/job-status/{{task_id}}/",
            "scheduled_jobs": f"{base_url}celery/scheduled/",
            "job_runs_history": f"{base_url}celery/runs/",
            "real_time_stats": f"{base_url}celery/api/dashboard-stats/"
        },
        
        # Frontend Integration
        "frontend_endpoints": {
            "dashboard": f"{base_url}",
            "jobs_interface": f"{base_url}jobs/",
            "companies_interface": f"{base_url}companies/", 
            "scraper_control": f"{base_url}scraper/",
            "admin_panel": f"{base_url}admin/"
        },
        
        # Real-time Features
        "real_time_features": {
            "htmx_endpoints": [
                f"{base_url}api/dashboard-stats/ (HTMX only)",
                f"{base_url}api/search-suggestions/ (HTMX only)",
                f"{base_url}api/jobs/{{id}}/delete/ (HTMX only)",
                f"{base_url}api/jobs/{{id}}/favorite/ (HTMX only)"
            ],
            "websocket_support": "Task progress tracking via Celery + Redis",
            "live_updates": "Auto-refresh dashboard with HTMX",
            "note": "HTMX endpoints require HX-Request header and return HTML fragments"
        }
    })

router = DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'jobs', JobViewSet)

urlpatterns = [
    path('', api_root, name='api-root'),
    path('', include(router.urls)),
]