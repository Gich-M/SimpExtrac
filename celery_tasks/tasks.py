"""
Celery tasks for job scraping functionality
"""
from celery import shared_task, current_task
from celery.exceptions import Retry
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
import logging
import traceback
import time
from typing import Dict, List, Any

# Set up logging
logger = logging.getLogger(__name__)


@shared_task(bind=True, name='celery_tasks.scrape_jobs_task')
def scrape_jobs_task(self, search_criteria: Dict[str, Any], scheduled_job_id=None, user_id=None):
    """
    Main task for scraping jobs with progress tracking
    
    Args:
        search_criteria: Dictionary containing search parameters
        scheduled_job_id: ID of scheduled job (None for manual runs)
        user_id: ID of user who triggered the task (for manual runs)
    """
    # Import here to avoid circular imports
    from .models import ScheduledScrapeJob, ScrapeJobRun, TaskProgress
    from jobs.models import Job, Company
    from scraper.tasks import run_scraper_task
    
    task_id = self.request.id
    
    # Create task progress tracker
    progress = TaskProgress.objects.create(
        task_id=task_id,
        current_step="Initializing scrape job...",
        total_sources=len(search_criteria.get('sources', ['indeed']))
    )
    
    # Create job run record
    job_run = ScrapeJobRun.objects.create(
        scheduled_job_id=scheduled_job_id,
        celery_task_id=task_id,
        search_criteria=search_criteria,
        triggered_by_id=user_id,
        status='running'
    )
    
    try:
        logger.info(f"Starting scrape task {task_id} with criteria: {search_criteria}")
        
        # Check if this is URL-based or legacy parameter-based scraping
        scrape_type = search_criteria.get('scrape_type', 'legacy')
        
        if scrape_type == 'url_based':
            # NEW: URL-based approach (Interview Requirement 6)
            filtered_url = search_criteria.get('filtered_url', '')
            max_jobs = search_criteria.get('max_jobs', 25)
            source = search_criteria.get('source', 'indeed')
            
            progress.update_progress(
                step=f"Starting URL-based scraping from {source.title()}",
                percentage=10
            )
            
            try:
                progress.update_progress(
                    step=f"Processing {filtered_url}...",
                    current_source=source,
                    percentage=30
                )
                
                jobs_before = Job.objects.count()
                companies_before = Company.objects.count()
                
                # Call the new URL-based scraper task
                from scraper.tasks import run_scraper_url_task
                scrape_results = run_scraper_url_task(
                    filtered_url=filtered_url,
                    max_jobs=max_jobs,
                    source=source
                )
                
                jobs_after = Job.objects.count()
                companies_after = Company.objects.count()
                
                jobs_found = jobs_after - jobs_before
                companies_found = companies_after - companies_before
                
                progress.update_progress(
                    step="URL-based scraping completed",
                    jobs_scraped=jobs_found,
                    companies_found=companies_found,
                    percentage=90
                )
                
                logger.info(f"URL-based scraping completed: {jobs_found} jobs, {companies_found} companies")
                
                # Final result for URL-based scraping
                total_jobs_found = jobs_found
                total_companies_found = companies_found
                source_results = {
                    source: {
                        'jobs_found': jobs_found,
                        'companies_found': companies_found,
                        'success': True
                    }
                }
                errors = []
                
            except Exception as e:
                error_msg = f"Error in URL-based scraping: {str(e)}"
                logger.error(f"Task {task_id} - {error_msg}")
                errors = [{'source': source, 'error': error_msg}]
                total_jobs_found = 0
                total_companies_found = 0
                source_results = {}
                
        else:
            # LEGACY: Parameter-based approach (redirects internally to URL-based)
            job_title = search_criteria.get('job_title', '')
            location = search_criteria.get('location', '')
            sources = search_criteria.get('sources', ['indeed'])
            max_jobs = search_criteria.get('max_jobs', 25)
            
            # Update progress
            progress.update_progress(
                step=f"Starting legacy scraping for '{job_title}' in '{location}'",
                percentage=5
            )
            
            # Track results
            total_jobs_found = 0
            total_companies_found = 0
            errors = []
            source_results = {}
            
            # Process each source
            for i, source in enumerate(sources):
                try:
                    progress.update_progress(
                        step=f"Scraping {source.title()}...",
                        current_source=source,
                        completed_sources=i,
                        percentage=10 + (i * 70 // len(sources))
                    )
                    
                    logger.info(f"Scraping {source} for task {task_id}")
                    
                    # Run the scraper for this source
                    jobs_before = Job.objects.count()
                    companies_before = Company.objects.count()
                    
                    # Call the legacy scraper task (redirects internally to URL-based)
                    scrape_results = run_scraper_task(
                        job_title=job_title,
                        location=location,
                        source=source,
                        max_jobs=max_jobs // len(sources)  # Distribute across sources
                    )
                    
                    jobs_after = Job.objects.count()
                    companies_after = Company.objects.count()
                    
                    jobs_found = jobs_after - jobs_before
                    companies_found = companies_after - companies_before
                    
                    total_jobs_found += jobs_found
                    total_companies_found += companies_found
                    
                    source_results[source] = {
                        'jobs_found': jobs_found,
                        'companies_found': companies_found,
                        'success': True
                    }
                    
                    # Update progress
                    progress.update_progress(
                        jobs_scraped=total_jobs_found,
                        companies_found=total_companies_found,
                        completed_sources=i + 1
                    )
                    
                    logger.info(f"Completed {source} scraping: {jobs_found} jobs, {companies_found} companies")
                    
                except Exception as e:
                    error_msg = f"Error scraping {source}: {str(e)}"
                    logger.error(f"Task {task_id} - {error_msg}")
                    logger.error(traceback.format_exc())
                    
                    errors.append({
                        'source': source,
                        'error': str(e),
                        'timestamp': timezone.now().isoformat()
                    })
                    
                    source_results[source] = {
                        'jobs_found': 0,
                        'companies_found': 0,
                        'success': False,
                        'error': str(e)
                    }
                    
                    # Continue with other sources even if one fails
                    continue
        
        # Final progress update
        progress.update_progress(
            step="Finalizing results...",
            percentage=90
        )
        
        # Update job run with results
        job_run.status = 'success' if not errors or total_jobs_found > 0 else 'failed'
        job_run.jobs_found = total_jobs_found
        job_run.companies_found = total_companies_found
        job_run.errors = errors
        job_run.result_summary = {
            'total_jobs_found': total_jobs_found,
            'total_companies_found': total_companies_found,
            'sources_processed': len(sources),
            'sources_with_errors': len([s for s in source_results.values() if not s['success']]),
            'source_results': source_results,
            'search_parameters': search_criteria
        }
        job_run.completed_at = timezone.now()
        job_run.save()
        
        # Update scheduled job last run time
        if scheduled_job_id:
            try:
                scheduled_job = ScheduledScrapeJob.objects.get(id=scheduled_job_id)
                scheduled_job.last_run = timezone.now()
                scheduled_job.save()
            except ScheduledScrapeJob.DoesNotExist:
                logger.warning(f"Scheduled job {scheduled_job_id} not found")
        
        # Complete progress tracking
        progress.update_progress(
            step=f"Completed! Found {total_jobs_found} jobs from {total_companies_found} companies",
            percentage=100
        )
        
        logger.info(f"Task {task_id} completed successfully: {total_jobs_found} jobs, {total_companies_found} companies")
        
        return {
            'success': True,
            'jobs_found': total_jobs_found,
            'companies_found': total_companies_found,
            'sources_processed': len(sources),
            'errors': errors,
            'task_id': task_id
        }
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error in scrape task: {str(e)}"
        logger.error(f"Task {task_id} - {error_msg}")
        logger.error(traceback.format_exc())
        
        # Update job run as failed
        job_run.status = 'failed'
        job_run.errors = [{'error': str(e), 'timestamp': timezone.now().isoformat()}]
        job_run.completed_at = timezone.now()
        job_run.save()
        
        # Update progress
        progress.update_progress(
            step=f"Failed: {str(e)}",
            percentage=100
        )
        
        # Re-raise the exception so Celery marks it as failed
        raise


@shared_task(name='celery_tasks.cleanup_old_progress')
def cleanup_old_progress():
    """
    Cleanup old task progress records (older than 24 hours)
    """
    from .models import TaskProgress
    from datetime import timedelta
    
    cutoff_time = timezone.now() - timedelta(hours=24)
    deleted_count = TaskProgress.objects.filter(created_at__lt=cutoff_time).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old progress records")
    return {'deleted_count': deleted_count}


@shared_task(name='celery_tasks.cleanup_old_job_runs')
def cleanup_old_job_runs():
    """
    Cleanup old job run records (keep last 100 per scheduled job)
    """
    from .models import ScheduledScrapeJob, ScrapeJobRun
    
    deleted_count = 0
    
    # For each scheduled job, keep only the last 100 runs
    for scheduled_job in ScheduledScrapeJob.objects.all():
        runs_to_delete = (
            ScrapeJobRun.objects
            .filter(scheduled_job=scheduled_job)
            .order_by('-started_at')[100:]
        )
        
        if runs_to_delete:
            count = runs_to_delete.delete()[0]
            deleted_count += count
    
    # Also cleanup manual runs (keep last 50)
    manual_runs_to_delete = (
        ScrapeJobRun.objects
        .filter(scheduled_job__isnull=True)
        .order_by('-started_at')[50:]
    )
    
    if manual_runs_to_delete:
        count = manual_runs_to_delete.delete()[0]
        deleted_count += count
    
    logger.info(f"Cleaned up {deleted_count} old job run records")
    return {'deleted_count': deleted_count}


@shared_task(name='celery_tasks.update_scheduled_job_next_run')
def update_scheduled_job_next_run():
    """
    Update next_run times for all active scheduled jobs
    This helps with UI display of when jobs will run next
    """
    from .models import ScheduledScrapeJob
    from datetime import timedelta
    
    updated_count = 0
    
    for job in ScheduledScrapeJob.objects.filter(is_active=True):
        try:
            # Calculate next run time based on schedule type
            now = timezone.now()
            
            if job.schedule_type == 'hourly':
                next_run = now + timedelta(hours=1)
            elif job.schedule_type == 'daily':
                next_run = now + timedelta(days=1)
            elif job.schedule_type == 'weekly':
                next_run = now + timedelta(weeks=1)
            elif job.schedule_type == 'custom' and job.cron_expression:
                # For custom cron, we'd need a cron parser library
                # For now, default to daily
                next_run = now + timedelta(days=1)
            else:
                next_run = now + timedelta(days=1)
            
            job.next_run = next_run
            job.save(update_fields=['next_run'])
            updated_count += 1
            
        except Exception as e:
            logger.error(f"Error updating next_run for job {job.id}: {e}")
    
    logger.info(f"Updated next_run for {updated_count} scheduled jobs")
    return {'updated_count': updated_count}