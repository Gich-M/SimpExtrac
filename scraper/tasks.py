"""
Django tasks for scraper app

Implements URL-based scraping:
- User provides filtered URL + max jobs count
- Auto-detects source from URL domain
- Uses Selenium + BeautifulSoup4 + requests
- Saves to Django models with duplicate handling
"""
import logging
import django
from django.conf import settings
from django.utils import timezone

# Ensure Django is configured
if not settings.configured:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SimpExtrac.settings')
    django.setup()

from jobs.models import Job, Company
from .indeed_scraper import IndeedScraper
from .glassdoor_scraper import GlassdoorScraper
from .linkedin_scraper import LinkedInScraper
from .company_info_extractor import CompanyInfoExtractor
from .models import ScraperStats
from .data_manager import JobDataManager

logger = logging.getLogger(__name__)


def run_scraper_url_task(filtered_url, num_jobs, source=None):
    """
    URL-based scraper function.
    
    User enters filtered URL + specifies number of jobs to scrape.
    
    Args:
        filtered_url: Pre-filtered job search URL from Indeed/Glassdoor/LinkedIn
        num_jobs: Number of jobs to scrape (required, specified by user)
        source: Auto-detected from URL or manually specified
        
    Returns:
        Dictionary with scraping results
    """
    # Set logging level to INFO to capture all debug information
    logging.getLogger().setLevel(logging.INFO)
    
    logger.info(f"Starting URL-based scraping: {filtered_url} (jobs: {num_jobs})")
    
    # Auto-detect source from URL
    if not source:
        if 'indeed.com' in filtered_url.lower():
            source = 'indeed'
        elif 'glassdoor.com' in filtered_url.lower():
            source = 'glassdoor'
        elif 'linkedin.com' in filtered_url.lower():
            source = 'linkedin'
        else:
            source = 'indeed'  # default fallback
    
    # Stats tracking
    stats_date = timezone.now().date()
    stats, created = ScraperStats.objects.get_or_create(
        source=source,
        date=stats_date,
        defaults={
            'jobs_found': 0,
            'jobs_saved': 0,
            'duplicates_skipped': 0,
            'total_scraping_time': 0.0
        }
    )
    
    stats.jobs_requested += num_jobs
    
    start_time = timezone.now()
    
    try:
        # Initialize scrapers
        scrapers = {
            'indeed': lambda: IndeedScraper(fetch_descriptions=True),
            'glassdoor': lambda: GlassdoorScraper(fetch_descriptions=True),
            'linkedin': lambda: LinkedInScraper(fetch_descriptions=True),
        }
        
        if source not in scrapers:
            raise ValueError(f"Unsupported source: {source}. Use 'indeed', 'glassdoor', or 'linkedin'")
        
        scraper = scrapers[source]()
        company_extractor = CompanyInfoExtractor()
        data_manager = JobDataManager()

        
        # URL-based scraping
        logger.info(f"Using {source} scraper with URL-based approach...")
        scraped_jobs = scraper.scrape_jobs(filtered_url, num_jobs)
        logger.info(f"Scraped {len(scraped_jobs)} jobs from {source}")
        
        # Update stats
        stats.jobs_found += len(scraped_jobs)
        
        if not scraped_jobs:
            stats.save()
            return {
                'jobs_saved': 0,
                'companies_created': 0,
                'source': source,
                'filtered_url': filtered_url,
                'errors': []
            }
        
        # Enhance with company info
        logger.info("=" * 60)
        logger.info("STARTING COMPANY ENHANCEMENT PROCESS")
        logger.info("=" * 60)
        logger.info(f"Jobs to enhance: {len(scraped_jobs)}")
        
        enhanced_jobs = []
        enhancement_success = 0
        enhancement_failed = 0
        
        for i, job_data in enumerate(scraped_jobs, 1):
            company_name = job_data.get('company', 'Unknown')
            job_title = job_data.get('title', 'Unknown')
            
            logger.info(f"\n--- ENHANCING JOB {i}/{len(scraped_jobs)} ---")
            logger.info(f"Job Title: {job_title}")
            logger.info(f"Company: {company_name}")
            
            try:
                logger.info(f"Calling company_extractor.enhance_job_with_company_info()...")
                enhanced_job = company_extractor.enhance_job_with_company_info(job_data)
                
                # Log enhancement results
                original_website = job_data.get('company_website')
                enhanced_website = enhanced_job.get('company_website')
                original_email = job_data.get('company_email')
                enhanced_email = enhanced_job.get('company_email')
                
                logger.info(f"Enhancement completed for {company_name}")
                logger.info(f"  Original website: {original_website}")
                logger.info(f"  Enhanced website: {enhanced_website}")
                logger.info(f"  Original email: {original_email}")
                logger.info(f"  Enhanced email: {enhanced_email}")
                
                if enhanced_website or enhanced_email:
                    logger.info(f"SUCCESS: Found company info for {company_name}")
                    enhancement_success += 1
                else:
                    logger.warning(f"NO INFO: No company info found for {company_name}")
                    enhancement_failed += 1
                
                enhanced_jobs.append(enhanced_job)
                
            except Exception as e:
                logger.error(f"ERROR: Company enhancement failed for {company_name}: {e}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                enhanced_jobs.append(job_data)
                enhancement_failed += 1

        # Update stats
        stats.company_enhancements_success += enhancement_success
        stats.company_enhancements_failed += enhancement_failed
        stats.last_url_used = filtered_url
        
        # Log enhancement summary
        logger.info("=" * 60)
        logger.info("COMPANY ENHANCEMENT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total jobs processed: {len(scraped_jobs)}")
        logger.info(f"Successful enhancements: {enhancement_success}")
        logger.info(f"Failed enhancements: {enhancement_failed}")
        logger.info(f"Success rate: {(enhancement_success/len(scraped_jobs)*100):.1f}%" if scraped_jobs else "0%")
        
        # Count jobs with actual company info
        jobs_with_websites = len([j for j in enhanced_jobs if j.get('company_website')])
        jobs_with_emails = len([j for j in enhanced_jobs if j.get('company_email')])
        
        logger.info(f"Jobs with websites: {jobs_with_websites}")
        logger.info(f"Jobs with emails: {jobs_with_emails}")
        logger.info("=" * 60)
        
        # Save to Django models
        data_manager.save_to_django_db(enhanced_jobs)

        # Result counting
        jobs_saved = len([job for job in enhanced_jobs if job.get('title') and job.get('company')])
        companies = set(job.get('company') for job in enhanced_jobs if job.get('company'))
        companies_created = len(companies)
        
        # Cleanup
        company_extractor.cleanup()
        
        # Update stats
        end_time = timezone.now()
        scraping_time = (end_time - start_time).total_seconds()
        
        stats.jobs_saved += jobs_saved
        stats.total_scraping_time += scraping_time
        stats.save()
        
        result = {
            'jobs_saved': jobs_saved,
            'companies_created': companies_created,
            'source': source,
            'filtered_url': filtered_url,
            'total_scraped': len(scraped_jobs),
            'scraping_time': scraping_time,
            'errors': []
        }

        logger.info(f"URL-based scraping completed: {jobs_saved} jobs saved from {filtered_url}")
        return result
        
    except Exception as e:
        logger.error(f"URL-based scraping failed: {str(e)}")
        raise