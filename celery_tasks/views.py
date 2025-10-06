"""
Views for scheduled job management and manual scraping
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .models import ScheduledScrapeJob, ScrapeJobRun, TaskProgress
from .tasks import scrape_jobs_task

logger = logging.getLogger(__name__)


def scheduled_jobs_list(request):
    """List all scheduled jobs"""
    jobs = ScheduledScrapeJob.objects.filter(created_by=request.user if request.user.is_authenticated else None)
    
    context = {
        'scheduled_jobs': jobs,
        'page_title': 'Scheduled Jobs',
    }
    return render(request, 'celery_tasks/scheduled_jobs.html', context)


@login_required
@require_http_methods(["POST"])
def trigger_manual_scrape(request):
    """Trigger a manual scraping job"""
    try:
        # Parse request data
        data = json.loads(request.body) if request.body else {}
        
        # Extract search criteria
        search_criteria = {
            'job_title': data.get('job_title', ''),
            'location': data.get('location', ''),
            'sources': data.get('sources', ['indeed']),
            'max_jobs': int(data.get('max_jobs', 25))
        }
        
        # Validate required fields
        if not search_criteria['job_title']:
            return JsonResponse({'error': 'Job title is required'}, status=400)
        
        # Submit task to Celery
        logger.info(f"User {request.user.username} triggered manual scrape: {search_criteria}")
        result = scrape_jobs_task.delay(search_criteria, user_id=request.user.id)
        
        return JsonResponse({
            'success': True,
            'task_id': result.id,
            'message': 'Scraping job started successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error triggering manual scrape: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def job_run_status(request, task_id):
    """Get status of a specific job run"""
    try:
        # Try to get job run by task ID
        job_run = ScrapeJobRun.objects.filter(celery_task_id=task_id).first()
        
        # Get task progress
        progress = TaskProgress.objects.filter(task_id=task_id).first()
        
        response_data = {
            'task_id': task_id,
            'status': job_run.status if job_run else 'unknown',
        }
        
        if job_run:
            response_data.update({
                'started_at': job_run.started_at.isoformat(),
                'completed_at': job_run.completed_at.isoformat() if job_run.completed_at else None,
                'jobs_found': job_run.jobs_found,
                'companies_found': job_run.companies_found,
                'errors': job_run.errors,
                'result_summary': job_run.result_summary,
            })
        
        if progress:
            response_data.update({
                'progress': {
                    'current_step': progress.current_step,
                    'percentage': progress.progress_percentage,
                    'total_sources': progress.total_sources,
                    'completed_sources': progress.completed_sources,
                    'current_source': progress.current_source,
                    'jobs_scraped': progress.jobs_scraped,
                    'companies_found': progress.companies_found,
                    'updated_at': progress.updated_at.isoformat(),
                }
            })
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error getting job status for {task_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def job_runs_list(request):
    """List recent job runs"""
    runs = ScrapeJobRun.objects.select_related('scheduled_job', 'triggered_by').order_by('-started_at')
    
    # Pagination
    paginator = Paginator(runs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'job_runs': page_obj,
        'page_title': 'Job Runs History',
    }
    return render(request, 'celery_tasks/job_runs.html', context)


@login_required
def create_scheduled_job(request):
    """Create a new scheduled job"""
    if request.method == 'POST':
        try:
            # Extract form data
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            job_title = request.POST.get('job_title', '').strip()
            location = request.POST.get('location', '').strip()
            sources = request.POST.getlist('sources')
            max_jobs = int(request.POST.get('max_jobs', 25))
            schedule_type = request.POST.get('schedule_type', 'daily')
            cron_expression = request.POST.get('cron_expression', '').strip()
            
            # Validate required fields
            if not name:
                messages.error(request, 'Job name is required')
                return redirect('celery_tasks:create_scheduled_job')
                
            if not job_title:
                messages.error(request, 'Job title is required')
                return redirect('celery_tasks:create_scheduled_job')
            
            if not sources:
                sources = ['indeed']
            
            # Create scheduled job
            scheduled_job = ScheduledScrapeJob.objects.create(
                name=name,
                description=description,
                job_title=job_title,
                location=location,
                sources=sources,
                max_jobs=max_jobs,
                schedule_type=schedule_type,
                cron_expression=cron_expression if schedule_type == 'custom' else '',
                created_by=request.user
            )
            
            messages.success(request, f'Scheduled job "{name}" created successfully')
            return redirect('celery_tasks:scheduled_jobs')
            
        except Exception as e:
            logger.error(f"Error creating scheduled job: {e}")
            messages.error(request, f'Error creating scheduled job: {e}')
    
    context = {
        'page_title': 'Create Scheduled Job',
    }
    return render(request, 'celery_tasks/create_scheduled_job.html', context)


@login_required
def toggle_scheduled_job(request, job_id):
    """Toggle active status of a scheduled job"""
    job = get_object_or_404(ScheduledScrapeJob, id=job_id, created_by=request.user)
    
    job.is_active = not job.is_active
    job.save()
    
    status = 'activated' if job.is_active else 'deactivated'
    messages.success(request, f'Job "{job.name}" {status} successfully')
    
    return redirect('celery_tasks:scheduled_jobs')


def api_dashboard_stats(request):
    """API endpoint for dashboard statistics"""
    try:
        # Get recent job runs (last 7 days)
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        
        recent_runs = ScrapeJobRun.objects.filter(started_at__gte=week_ago)
        active_scheduled_jobs = ScheduledScrapeJob.objects.filter(is_active=True).count()
        
        # Calculate statistics
        total_runs = recent_runs.count()
        successful_runs = recent_runs.filter(status='success').count()
        failed_runs = recent_runs.filter(status='failed').count()
        running_jobs = recent_runs.filter(status__in=['pending', 'running']).count()
        
        # Get total jobs and companies
        from jobs.models import Job, Company
        total_jobs = Job.objects.count()
        total_companies = Company.objects.count()
        
        stats = {
            'active_scheduled_jobs': active_scheduled_jobs,
            'total_job_runs_week': total_runs,
            'successful_runs_week': successful_runs,
            'failed_runs_week': failed_runs,
            'currently_running': running_jobs,
            'total_jobs_scraped': total_jobs,
            'total_companies': total_companies,
            'success_rate': round((successful_runs / total_runs * 100), 1) if total_runs > 0 else 0,
        }
        
        return JsonResponse(stats)
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return JsonResponse({'error': str(e)}, status=500)
