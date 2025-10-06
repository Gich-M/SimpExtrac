"""
Django tasks for the scraper app - these are the actual scraping functions
that can be called from Celery tasks or Django management commands
"""
import logging
import django
from django.conf import settings
from django.utils import timezone

# Ensure Django is configured
if not settings.configured:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpextrac.settings')
    django.setup()

from jobs.models import Job, Company
from .indeed_scraper import IndeedScraper
from .glassdoor_scraper import GlassdoorScraper  
from .company_info_extractor import CompanyInfoExtractor
from .models import ScraperStats

logger = logging.getLogger(__name__)


def run_scraper_task(job_title, location, source='indeed', max_jobs=25):
    """
    Main scraper function that can be called from Celery tasks or management commands
    
    Args:
        job_title: Job title to search for
        location: Location to search in  
        source: Source to scrape ('indeed', 'glassdoor')
        max_jobs: Maximum number of jobs to scrape
        
    Returns:
        Dictionary with results
    """
    logger.info(f"Starting {source} scraping for '{job_title}' in '{location}'")
    
    # Track stats
    stats_date = timezone.now().date()
    stats, created = ScraperStats.objects.get_or_create(
        source=source,
        date=stats_date,
        defaults={
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'jobs_found': 0,
            'jobs_saved': 0,
            'duplicates_skipped': 0
        }
    )
    
    start_time = timezone.now()
    
    try:
        # Initialize scrapers
        scrapers = {
            'indeed': lambda: IndeedScraper(fetch_descriptions=True),
            'glassdoor': lambda: GlassdoorScraper()
        }
        
        if source not in scrapers:
            raise ValueError(f"Unsupported source: {source}")
        
        scraper = scrapers[source]()
        company_extractor = CompanyInfoExtractor(use_selenium=False)
        
        # Scrape jobs
        scraped_jobs = scraper.scrape_jobs(job_title, location, max_jobs)
        logger.info(f"Scraped {len(scraped_jobs)} jobs from {source}")
        
        # Update stats
        stats.requests_made += 1
        stats.jobs_found += len(scraped_jobs)
        
        if not scraped_jobs:
            stats.successful_requests += 1
            stats.save()
            return {
                'jobs_saved': 0,
                'companies_created': 0,
                'source': source,
                'errors': []
            }
        
        # Save to Django models
        jobs_saved = 0
        companies_created = 0
        duplicates_skipped = 0
        errors = []
        
        for job_data in scraped_jobs:
            try:
                # Get or create company
                company_name = job_data.get('company', '').strip()
                if not company_name:
                    continue
                
                company, created = Company.objects.get_or_create(
                    name=company_name,
                    defaults={
                        'description': job_data.get('company_description', ''),
                        'company_website': job_data.get('company_website', ''),
                        'company_email': job_data.get('company_email', ''),
                        'industry': job_data.get('industry', ''),
                    }
                )
                
                if created:
                    companies_created += 1
                    logger.info(f"Created new company: {company_name}")
                
                # Create job (with unique constraint handling)
                job, job_created = Job.objects.get_or_create(
                    title=job_data.get('title', '').strip(),
                    company=company,
                    location=job_data.get('location', '').strip(),
                    defaults={
                        'url': job_data.get('url', ''),
                        'description': job_data.get('description', ''),
                        'salary': job_data.get('salary', ''),
                        'source': source.title(),
                    }
                )
                
                if job_created:
                    jobs_saved += 1
                    logger.info(f"Saved new job: {job_data.get('title')} at {company_name}")
                else:
                    duplicates_skipped += 1
                    logger.info(f"Job already exists: {job_data.get('title')} at {company_name}")
                    
            except Exception as e:
                error_msg = f"Error saving job {job_data.get('title', 'Unknown')}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Cleanup
        company_extractor.cleanup()
        
        # Update stats
        end_time = timezone.now()
        scraping_time = (end_time - start_time).total_seconds()
        
        stats.successful_requests += 1
        stats.jobs_saved += jobs_saved
        stats.duplicates_skipped += duplicates_skipped
        stats.total_scraping_time += scraping_time
        
        # Update average response time
        if stats.successful_requests > 0:
            stats.average_response_time = stats.total_scraping_time / stats.successful_requests
        
        if errors:
            stats.error_details.extend(errors)
        
        stats.save()
        
        result = {
            'jobs_saved': jobs_saved,
            'companies_created': companies_created,
            'duplicates_skipped': duplicates_skipped,
            'source': source,
            'errors': errors,
            'total_scraped': len(scraped_jobs),
            'scraping_time': scraping_time
        }
        
        logger.info(f"Scraping completed: {jobs_saved} jobs saved, {companies_created} companies created")
        return result
        
    except Exception as e:
        # Update error stats
        stats.failed_requests += 1
        stats.error_details.append({
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
            'search_criteria': {
                'job_title': job_title,
                'location': location,
                'max_jobs': max_jobs
            }
        })
        stats.save()
        
        logger.error(f"Scraping failed: {str(e)}")
        raise


def get_scraper_stats(source=None, days=7):
    """
    Get scraper statistics for the last N days
    
    Args:
        source: Specific source to get stats for (optional)
        days: Number of days to look back
        
    Returns:
        QuerySet of ScraperStats
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now().date() - timedelta(days=days)
    
    queryset = ScraperStats.objects.filter(date__gte=cutoff_date)
    
    if source:
        queryset = queryset.filter(source=source)
    
    return queryset.order_by('-date', 'source')