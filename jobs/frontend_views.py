from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
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
        
        # Data for visualizations
        from django.db.models import Count
        from datetime import timedelta
        import json
        
        # Source distribution data
        source_stats = (Job.objects.values('source')
                       .annotate(count=Count('id'))
                       .order_by('-count'))
        context['source_stats'] = json.dumps(list(source_stats))
        
        # Top companies (for chart)
        top_companies = (Job.objects.values('company__name')
                        .annotate(count=Count('id'))
                        .order_by('-count')[:10])
        context['top_companies'] = json.dumps(list(top_companies))
        
        # Top locations (for chart)
        top_locations_data = (Job.objects.values('location')
                        .annotate(count=Count('id'))
                        .order_by('-count')[:8])
        context['top_locations'] = json.dumps(list(top_locations_data))
        context['top_locations_list'] = list(top_locations_data)  # For template loop
        
        # Activity data for last 7 days
        activity_data = []
        for i in range(6, -1, -1):  # Last 7 days
            date = timezone.now().date() - timedelta(days=i)
            jobs_count = Job.objects.filter(created_at__date=date).count()
            activity_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'date_label': date.strftime('%m/%d'),
                'count': jobs_count
            })
        context['activity_data'] = json.dumps(activity_data)
        
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
        
        # Get filter parameters from GET only
        search = self.request.GET.get('search', '').strip()
        source = self.request.GET.get('source', '').strip()
        location = self.request.GET.get('location', '').strip()
        company = self.request.GET.get('company', '').strip()
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"JobListView filters - search: '{search}', source: '{source}', location: '{location}', company: '{company}'")
        
        initial_count = queryset.count()
        logger.info(f"Initial queryset count: {initial_count}")
        
        # Search functionality
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(company__name__icontains=search) |
                Q(description__icontains=search) |
                Q(location__icontains=search)
            )
            logger.info(f"After search filter '{search}': {queryset.count()}")
        
        # Source filter - handle case variations
        if source:
            # Check what sources actually exist in the database
            existing_sources = Job.objects.values_list('source', flat=True).distinct()
            logger.info(f"Existing sources in DB: {list(existing_sources)}")
            
            # Try case-insensitive matching
            queryset = queryset.filter(source__iexact=source)
            logger.info(f"After source filter '{source}' (case-insensitive): {queryset.count()}")
            
        # Location filter
        if location:
            queryset = queryset.filter(location__icontains=location)
            logger.info(f"After location filter '{location}': {queryset.count()}")
            
        # Company filter
        if company:
            queryset = queryset.filter(company__name__icontains=company)
            logger.info(f"After company filter '{company}': {queryset.count()}")
        
        final_count = queryset.count()
        logger.info(f"Final queryset count: {final_count}")
        
        return queryset
    
    def get_template_names(self):
        if self.request.htmx:
            return ['jobs/job_list_partial.html']
        return ['jobs/job_list.html']


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
    """
    HTMX-powered scraper control with URL-based input (Interview Requirement 6).
    
    User enters filtered URL + specifies number of jobs to scrape.
    """
    
    if request.method == 'POST':
        # NEW: URL-based approach (requirement 6)
        filtered_url = request.POST.get('filtered_url', '')
        max_jobs = int(request.POST.get('max_jobs', 10))
        
        # Auto-detect source from URL domain
        source = 'indeed'  # default
        if 'glassdoor.com' in filtered_url.lower():
            source = 'glassdoor'
        elif 'linkedin.com' in filtered_url.lower():
            source = 'linkedin'
        elif 'indeed.com' in filtered_url.lower():
            source = 'indeed'
        
        if request.htmx:
            # For HTMX requests, run scraping task
            try:
                # Use URL-based scraping (requirement 6)
                if max_jobs <= 25:
                    from celery_tasks.tasks import scrape_jobs_task
                    
                    # Prepare URL-based search criteria
                    search_criteria = {
                        'filtered_url': filtered_url,
                        'max_jobs': max_jobs,
                        'source': source,
                        'scrape_type': 'url_based'  # New flag for URL-based scraping
                    }
                    
                    task = scrape_jobs_task.delay(
                        search_criteria=search_criteria,
                        user_id=request.user.id if request.user.is_authenticated else None
                    )
                    
                    # Return task status for URL-based scraping
                    return render(request, 'scraper/scraper_results.html', {
                        'status': 'running',
                        'task_id': task.id,
                        'search_params': {
                            'filtered_url': filtered_url,
                            'max_jobs': max_jobs,
                            'source': source
                        }
                    })
                else:
                    # For larger jobs, always use background processing
                    try:
                        from celery_tasks.tasks import scrape_jobs_task
                        
                        search_criteria = {
                            'filtered_url': filtered_url,
                            'max_jobs': max_jobs,
                            'source': source,
                            'scrape_type': 'url_based'
                        }
                        
                        task = scrape_jobs_task.delay(
                            search_criteria=search_criteria,
                            user_id=request.user.id if request.user.is_authenticated else None
                        )
                        
                        # Return background task status
                        return render(request, 'scraper/scraper_results.html', {
                            'status': 'running',
                            'task_id': task.id,
                            'search_params': {
                                'filtered_url': filtered_url,
                                'max_jobs': max_jobs,
                                'source': source
                            }
                        })
                    except Exception as e:
                        # Return error result
                        return render(request, 'scraper/scraper_results.html', {
                            'status': 'error',
                            'error_message': f'Failed to queue background job: {str(e)}',
                            'search_params': {
                                'filtered_url': filtered_url,
                                'max_jobs': max_jobs,
                                'source': source
                            }
                        })
                        
            except Exception as e:
                # Return error result
                return render(request, 'scraper/scraper_results.html', {
                    'status': 'error',
                    'error_message': str(e),
                    'search_params': {
                        'filtered_url': filtered_url,
                        'max_jobs': max_jobs,
                        'source': source
                    }
                })
        else:
            # Handle non-HTMX POST (redirect after POST)
            messages.info(request, 'Scraping job submitted!')
            return HttpResponseRedirect(request.path)
    
    # GET request - show the scraper control page
    # Get last scan summary
    try:
        from scraper.models import ScraperStats
        last_scan = ScraperStats.objects.filter(
            jobs_found__gt=0
        ).order_by('-date').first()
    except:
        last_scan = None
    
    return render(request, 'scraper/scraper_control.html', {
        'last_scan': last_scan
    })


@require_http_methods(["POST"])
def schedule_scraping(request):
    """Schedule a recurring scraping task using Celery Beat with enhanced timing options"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    job_title = request.POST.get('job_title')
    location = request.POST.get('location', 'Remote')
    interval = request.POST.get('interval', 'daily')
    schedule_time = request.POST.get('schedule_time', '09:00')
    timezone = request.POST.get('timezone', 'UTC')
    schedule_sources = request.POST.getlist('schedule_sources')
    
    if not schedule_sources:
        schedule_sources = ['indeed']  # Default to indeed if none selected
    
    if not job_title:
        return render(request, 'scraper/schedule_error.html', {
            'error': 'Job title is required'
        })
    
    try:
        from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
        from django.utils import timezone as django_tz
        from datetime import datetime, timedelta
        import json
        
        # Parse the time
        time_parts = schedule_time.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        schedule = None
        task_name = f"Scheduled Scrape: {job_title} in {location}"
        
        # Handle different interval types
        if interval == 'custom':
            custom_minutes = request.POST.get('custom_minutes')
            if not custom_minutes:
                return render(request, 'scraper/schedule_error.html', {
                    'error': 'Custom interval minutes required'
                })
            
            try:
                minutes = int(custom_minutes)
                if minutes < 1 or minutes > 1440:
                    raise ValueError("Invalid range")
            except ValueError:
                return render(request, 'scraper/schedule_error.html', {
                    'error': 'Custom interval must be between 1 and 1440 minutes'
                })
            
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=minutes,
                period=IntervalSchedule.MINUTES,
            )
            task_name += f" (every {minutes}min)"
            
        elif interval == '30min':
            schedule, created = IntervalSchedule.objects.get_or_create(
                every=30,
                period=IntervalSchedule.MINUTES,
            )
            task_name += " (every 30min)"
            
        elif interval == 'hourly':
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute=minute, hour='*',
                day_of_week='*', day_of_month='*', month_of_year='*'
            )
            task_name += f" (hourly at :{minute:02d})"
            
        elif interval == 'daily':
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour,
                day_of_week='*', day_of_month='*', month_of_year='*'
            )
            task_name += f" (daily at {hour:02d}:{minute:02d})"
            
        elif interval == 'weekly':
            days_of_week = request.POST.getlist('days_of_week')
            if not days_of_week:
                days_of_week = ['1']  # Default to Monday
            
            days_str = ','.join(days_of_week)
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour,
                day_of_week=days_str, day_of_month='*', month_of_year='*'
            )
            
            day_names = {
                '0': 'Sun', '1': 'Mon', '2': 'Tue', '3': 'Wed',
                '4': 'Thu', '5': 'Fri', '6': 'Sat'
            }
            selected_days = [day_names[day] for day in days_of_week]
            task_name += f" ({','.join(selected_days)} at {hour:02d}:{minute:02d})"
            
        elif interval == 'monthly':
            day_of_month = request.POST.get('day_of_month', '1')
            
            if day_of_month == 'last':
                # Last day of month (approximation using day 28-31)
                schedule, created = CrontabSchedule.objects.get_or_create(
                    minute=minute, hour=hour,
                    day_of_week='*', day_of_month='28-31', month_of_year='*'
                )
                task_name += f" (last day at {hour:02d}:{minute:02d})"
            else:
                schedule, created = CrontabSchedule.objects.get_or_create(
                    minute=minute, hour=hour,
                    day_of_week='*', day_of_month=day_of_month, month_of_year='*'
                )
                task_name += f" ({day_of_month}th at {hour:02d}:{minute:02d})"
                
        elif interval == 'once':
            # One-time task
            schedule_date = request.POST.get('schedule_date')
            if not schedule_date:
                return render(request, 'scraper/schedule_error.html', {
                    'error': 'Date is required for one-time scheduling'
                })
            
            # Parse the datetime
            schedule_datetime = datetime.strptime(f"{schedule_date} {schedule_time}", "%Y-%m-%d %H:%M")
            
            # Check if it's in the future
            if schedule_datetime <= datetime.now():
                return render(request, 'scraper/schedule_error.html', {
                    'error': 'Scheduled time must be in the future'
                })
            
            # For one-time tasks, create a crontab for the specific date/time
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour,
                day_of_week='*', 
                day_of_month=schedule_datetime.day, 
                month_of_year=schedule_datetime.month
            )
            task_name += f" (once on {schedule_date} at {hour:02d}:{minute:02d})"
            
        else:
            return render(request, 'scraper/schedule_error.html', {
                'error': 'Invalid interval type'
            })
        
        # Check if task already exists
        if PeriodicTask.objects.filter(name=task_name).exists():
            return render(request, 'scraper/schedule_error.html', {
                'error': 'A scheduled task with this configuration already exists'
            })
        
        # Create the periodic task
        periodic_task = PeriodicTask.objects.create(
            name=task_name,
            task='celery_tasks.tasks.scrape_jobs_task',
            args=json.dumps([]),
            kwargs=json.dumps({
                'job_title': job_title,
                'location': location,
                'sources': schedule_sources,
                'max_jobs': 25
            }),
            enabled=True
        )
        
        # Assign the appropriate schedule
        if interval in ['custom', '30min']:
            periodic_task.interval = schedule
        else:
            periodic_task.crontab = schedule
        
        periodic_task.save()
        
        return render(request, 'scraper/schedule_success.html', {
            'task': periodic_task,
            'job_title': job_title,
            'location': location,
            'interval': interval
        })
        
    except Exception as e:
        return render(request, 'scraper/schedule_error.html', {
            'error': f'Failed to schedule task: {str(e)}'
        })


@require_http_methods(["GET"])
def scheduled_tasks(request):
    """Get list of scheduled scraping tasks"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    try:
        from django_celery_beat.models import PeriodicTask
        
        tasks = PeriodicTask.objects.filter(
            task='celery_tasks.tasks.scrape_jobs_task',
            enabled=True
        ).order_by('-date_changed')
        
        return render(request, 'scraper/scheduled_tasks.html', {
            'tasks': tasks
        })
        
    except Exception as e:
        return render(request, 'scraper/schedule_error.html', {
            'error': f'Failed to load scheduled tasks: {str(e)}'
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


@require_http_methods(["POST"])
def toggle_scheduled_task(request, task_id):
    """HTMX endpoint to toggle scheduled task enabled/disabled"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    try:
        from django_celery_beat.models import PeriodicTask
        
        task = get_object_or_404(PeriodicTask, id=task_id)
        task.enabled = not task.enabled
        task.save()
        
        action = "enabled" if task.enabled else "disabled"
        messages.success(request, f'Task "{task.name}" {action} successfully')
        
        return render(request, 'scraper/scheduled_task_item.html', {'task': task})
        
    except Exception as e:
        return render(request, 'scraper/schedule_error.html', {
            'error': f'Failed to toggle task: {str(e)}'
        })


@require_http_methods(["DELETE"])
def delete_scheduled_task(request, task_id):
    """HTMX endpoint to delete a scheduled task"""
    if not request.htmx:
        return JsonResponse({'error': 'HTMX required'}, status=400)
    
    try:
        from django_celery_beat.models import PeriodicTask
        
        task = get_object_or_404(PeriodicTask, id=task_id)
        task_name = task.name
        task.delete()
        
        messages.success(request, f'Scheduled task "{task_name}" deleted successfully')
        return HttpResponse('')  # Empty response triggers HTMX to remove the element
        
    except Exception as e:
        return render(request, 'scraper/schedule_error.html', {
            'error': f'Failed to delete task: {str(e)}'
        })