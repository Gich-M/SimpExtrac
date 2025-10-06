from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils import timezone
from django_htmx.http import HttpResponseClientRedirect
from .models import Job, Company
import json


class DashboardView(ListView):
    """Dashboard with HTMX-powered stats and recent jobs"""
    template_name = 'dashboard.html'
    context_object_name = 'recent_jobs'
    queryset = Job.objects.select_related('company').order_by('-created_at')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['stats'] = {
            'total_jobs': Job.objects.count(),
            'total_companies': Company.objects.count(),
            'jobs_today': Job.objects.filter(created_at__date=timezone.now().date()).count(),
            'companies_with_websites': Company.objects.exclude(company_website__isnull=True).exclude(company_website='').count(),
        }
        
        # Recent activity
        context['recent_companies'] = Company.objects.order_by('-created_at')[:5]
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class JobListView(ListView):
    """HTMX-powered job list with filtering and search"""
    model = Job
    template_name = 'jobs/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Job.objects.select_related('company').order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search') or self.request.POST.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(company__name__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
        
        # Filters
        source = self.request.GET.get('source') or self.request.POST.get('source')
        if source:
            queryset = queryset.filter(source=source)
            
        location = self.request.GET.get('location') or self.request.POST.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)
            
        company = self.request.GET.get('company') or self.request.POST.get('company')
        if company:
            queryset = queryset.filter(company__name__icontains=company)
        
        return queryset
    
    def get_template_names(self):
        if self.request.htmx:
            return ['jobs/job_list_partial.html']
        return ['jobs/job_list.html']
    
    def post(self, request, *args, **kwargs):
        """Handle HTMX POST requests for filtering"""
        return self.get(request, *args, **kwargs)


class JobDetailView(DetailView):
    """Job detail with HTMX enhancements"""
    model = Job
    template_name = 'jobs/job_detail.html'
    context_object_name = 'job'
    
    def get_template_names(self):
        if self.request.htmx:
            return ['jobs/job_detail_partial.html']
        return ['jobs/job_detail.html']


@method_decorator(csrf_exempt, name='dispatch')
class CompanyListView(ListView):
    """HTMX-powered company list"""
    model = Company
    template_name = 'companies/company_list.html'
    context_object_name = 'companies'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Company.objects.annotate(
            job_count=Count('jobs')
        ).order_by('-job_count', 'name')
        
        # Search functionality
        search = self.request.GET.get('search') or self.request.POST.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(company_website__icontains=search) |
                Q(company_email__icontains=search)
            )
        
        return queryset
    
    def get_template_names(self):
        if self.request.htmx:
            return ['companies/company_list_partial.html']
        return ['companies/company_list.html']
    
    def post(self, request, *args, **kwargs):
        """Handle HTMX POST requests for filtering"""
        return self.get(request, *args, **kwargs)


class CompanyDetailView(DetailView):
    """Company detail with related jobs"""
    model = Company
    template_name = 'companies/company_detail.html'
    context_object_name = 'company'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_jobs'] = Job.objects.filter(company=self.object).order_by('-created_at')
        return context
    
    def get_template_names(self):
        if self.request.htmx:
            return ['companies/company_detail_partial.html']
        return ['companies/company_detail.html']


@require_http_methods(["GET", "POST"])
def scraper_control(request):
    """HTMX-powered scraper control interface"""
    from scraper.main import main_scraper
    import threading
    
    if request.method == 'POST' and request.htmx:
        job_title = request.POST.get('job_title', 'Python Developer')
        location = request.POST.get('location', 'Remote')
        num_jobs = int(request.POST.get('num_jobs', 10))
        
        # Start scraping in background thread
        def run_scraper():
            try:
                main_scraper(job_title=job_title, location=location, num_jobs=num_jobs)
                messages.success(request, f'Successfully scraped jobs for "{job_title}" in "{location}"')
            except Exception as e:
                messages.error(request, f'Scraping failed: {str(e)}')
        
        thread = threading.Thread(target=run_scraper)
        thread.daemon = True
        thread.start()
        
        messages.info(request, 'Scraping started! Check back in a few minutes.')
        
        if request.htmx:
            return render(request, 'scraper/scraper_status.html', {
                'status': 'running',
                'message': 'Scraping in progress...'
            })
    
    # Get recent scraping activity
    recent_jobs = Job.objects.select_related('company').order_by('-created_at')[:10]
    
    # Statistics
    stats = {
        'total_jobs': Job.objects.count(),
        'indeed_jobs': Job.objects.filter(source='indeed').count(),
        'glassdoor_jobs': Job.objects.filter(source='glassdoor').count(),
        'total_companies': Company.objects.count(),
    }
    
    template = 'scraper/scraper_control.html'
    if request.htmx:
        template = 'scraper/scraper_control_partial.html'
    
    return render(request, template, {
        'recent_jobs': recent_jobs,
        'stats': stats
    })


@require_http_methods(["GET"])
def dashboard_stats(request):
    """HTMX endpoint for live dashboard stats"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    from django.utils import timezone
    
    stats = {
        'total_jobs': Job.objects.count(),
        'total_companies': Company.objects.count(),
        'jobs_today': Job.objects.filter(created_at__date=timezone.now().date()).count(),
        'companies_with_websites': Company.objects.exclude(company_website__isnull=True).exclude(company_website='').count(),
    }
    
    return render(request, 'dashboard_stats_partial.html', {'stats': stats})


@require_http_methods(["GET"])
def job_search_suggestions(request):
    """HTMX endpoint for search suggestions"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return HttpResponse('')
    
    # Search in job titles and company names
    job_suggestions = Job.objects.filter(
        title__icontains=query
    ).values_list('title', flat=True).distinct()[:5]
    
    company_suggestions = Company.objects.filter(
        name__icontains=query
    ).values_list('name', flat=True).distinct()[:5]
    
    return render(request, 'components/search_suggestions.html', {
        'job_suggestions': job_suggestions,
        'company_suggestions': company_suggestions,
        'query': query
    })


# API-like endpoints for HTMX
@require_http_methods(["DELETE"])
def delete_job(request, job_id):
    """HTMX endpoint to delete a job"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    job = get_object_or_404(Job, id=job_id)
    job_title = job.title
    job.delete()
    
    messages.success(request, f'Job "{job_title}" deleted successfully')
    return HttpResponse('')  # Empty response triggers HTMX to remove the element


@require_http_methods(["POST"])
def toggle_job_favorite(request, job_id):
    """HTMX endpoint to toggle job favorite status"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    job = get_object_or_404(Job, id=job_id)
    # Assuming you add a 'favorited' field to Job model
    # job.favorited = not job.favorited
    # job.save()
    
    return render(request, 'components/favorite_button.html', {'job': job})