from django.urls import path
from . import frontend_views

app_name = 'jobs'

urlpatterns = [
    # Main pages
    path('', frontend_views.DashboardView.as_view(), name='dashboard'),
    path('jobs/', frontend_views.JobListView.as_view(), name='jobs_list'),
    path('jobs/<int:pk>/', frontend_views.JobDetailView.as_view(), name='job_detail'),
    path('companies/', frontend_views.CompanyListView.as_view(), name='companies_list'),
    path('companies/<int:pk>/', frontend_views.CompanyDetailView.as_view(), name='company_detail'),
    path('scraper/', frontend_views.scraper_control, name='scraper_control'),
    
    # HTMX endpoints
    path('api/dashboard-stats/', frontend_views.dashboard_stats, name='dashboard_stats'),
    path('api/search-suggestions/', frontend_views.job_search_suggestions, name='search_suggestions'),
    path('api/jobs/<int:job_id>/delete/', frontend_views.delete_job, name='delete_job'),
    path('api/jobs/<int:job_id>/favorite/', frontend_views.toggle_job_favorite, name='toggle_favorite'),
]