"""
Main scraper script - can be run standalone or imported by Django
"""
import sys
import os

# Add the project root to the Python path for standalone execution
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time

# Django setup for when running as script
def setup_django():
    """Setup Django environment if not already configured"""
    try:
        import django
        from django.conf import settings
        
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'simpextrac.settings')
            django.setup()
        return True
    except ImportError:
        # Django not available, run in standalone mode
        return False

# Check if Django is available
DJANGO_AVAILABLE = setup_django()

# Import scrapers (always available)
try:
    from .indeed_scraper import IndeedScraper
    from .glassdoor_scraper import GlassdoorScraper  
    from .company_info_extractor import CompanyInfoExtractor
    from .data_manager import JobDataManager
except ImportError:
    # Standalone mode imports
    from indeed_scraper import IndeedScraper
    from glassdoor_scraper import GlassdoorScraper  
    from company_info_extractor import CompanyInfoExtractor
    from data_manager import JobDataManager

# Try to import Django components (optional)
try:
    if DJANGO_AVAILABLE:
        from .tasks import run_scraper_task
except ImportError:
    run_scraper_task = None


def run_django_scraper(job_title, location, sources=['indeed'], max_jobs=25):
    """
    Run scraper using Django integration (saves to database)
    """
    if not DJANGO_AVAILABLE or not run_scraper_task:
        raise RuntimeError("Django integration not available")
    
    results = []
    for source in sources:
        result = run_scraper_task(
            job_title=job_title,
            location=location,
            source=source,
            max_jobs=max_jobs // len(sources)
        )
        results.append(result)
    
    return results


def run_standalone_scraper(job_title="Python Developer", location="Remote", max_jobs_per_source=20):
    """
    Original standalone scraper (saves to JSON files)
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    indeed_scraper = IndeedScraper(fetch_descriptions=True)
    glassdoor_scraper = GlassdoorScraper()
    company_extractor = CompanyInfoExtractor(use_selenium=False)
    data_manager = JobDataManager("data/jobs.json")

    all_jobs = []

    try:
        # Test Indeed scraping first
        logging.info("Starting Indeed scraping...")
        indeed_jobs = indeed_scraper.scrape_jobs(job_title, location, max_jobs_per_source)
        all_jobs.extend(indeed_jobs)
        logging.info(f"Scraped {len(indeed_jobs)} jobs from Indeed")

        time.sleep(5)

        logging.info("Starting Glassdoor scraping...")
        glassdoor_jobs = glassdoor_scraper.scrape_jobs(job_title, location, max_jobs_per_source)
        all_jobs.extend(glassdoor_jobs)
        logging.info(f"Scraped {len(glassdoor_jobs)} jobs from Glassdoor")

        # Enhance jobs with company information (balanced across sources)
        logging.info("Enhancing jobs with company information...")
        enhanced_jobs = []
        
        # If no new jobs were scraped, use existing jobs for testing
        if not all_jobs:
            logging.info("No new jobs scraped, loading existing jobs for enhancement testing...")
            existing_jobs = data_manager.load_jobs()
            # Filter for jobs without company websites to enhance
            jobs_to_enhance_candidates = [job for job in existing_jobs if not job.get('company_website')]
            
            # Separate by source for balanced enhancement
            indeed_candidates = [job for job in jobs_to_enhance_candidates if job.get('source') == 'Indeed']
            glassdoor_candidates = [job for job in jobs_to_enhance_candidates if job.get('source') == 'Glassdoor']
            
            # Select jobs to enhance
            jobs_to_enhance = []
            jobs_to_enhance.extend(indeed_candidates[:5])     # First 5 Indeed jobs  
            jobs_to_enhance.extend(glassdoor_candidates[:5])  # First 5 Glassdoor jobs
            
            logging.info(f"Selected {len(jobs_to_enhance)} existing jobs for enhancement: {len(indeed_candidates[:5])} Indeed + {len(glassdoor_candidates[:5])} Glassdoor")
            
            # Process enhanced jobs
            for i, job in enumerate(jobs_to_enhance):
                try:
                    source = job.get('source', 'Unknown')
                    logging.info(f"Processing job {i+1}/{len(jobs_to_enhance)}: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')} [{source}]")
                    enhanced_job = company_extractor.enhance_job_with_company_info(job)
                    enhanced_jobs.append(enhanced_job)

                    # Add delay to be respectful to search engines
                    time.sleep(2)

                except Exception as e:
                    logging.error(f"Failed to enhance job {i+1}: {e}")
                    enhanced_jobs.append(job)
            
            # Update the original jobs with enhanced info
            for enhanced_job in enhanced_jobs:
                for i, existing_job in enumerate(existing_jobs):
                    if (existing_job.get('title') == enhanced_job.get('title') and 
                        existing_job.get('company') == enhanced_job.get('company')):
                        existing_jobs[i] = enhanced_job
                        break
            
            enhanced_jobs = existing_jobs
            
        else:
            # Normal flow for newly scraped jobs
            # Separate jobs by source for balanced enhancement
            indeed_jobs = [job for job in all_jobs if job.get('source') == 'Indeed']
            glassdoor_jobs = [job for job in all_jobs if job.get('source') == 'Glassdoor']
            
            # Select jobs proportionally from each source (balanced enhancement)
            jobs_to_enhance = []
            jobs_to_enhance.extend(indeed_jobs[:5])     # First 5 Indeed jobs  
            jobs_to_enhance.extend(glassdoor_jobs[:5])  # First 5 Glassdoor jobs
            
            # Remaining jobs that won't be enhanced
            jobs_remaining = indeed_jobs[5:] + glassdoor_jobs[5:]
            
            logging.info(f"Selected {len(jobs_to_enhance)} jobs for enhancement: {len(indeed_jobs[:5])} Indeed + {len(glassdoor_jobs[:5])} Glassdoor")

            for i, job in enumerate(jobs_to_enhance):
                try:
                    source = job.get('source', 'Unknown')
                    logging.info(f"Processing job {i+1}/{len(jobs_to_enhance)}: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')} [{source}]")
                    enhanced_job = company_extractor.enhance_job_with_company_info(job)
                    enhanced_jobs.append(enhanced_job)

                    # Add delay to be respectful to search engines
                    time.sleep(3)

                except Exception as e:
                    logging.error(f"Failed to enhance job {i+1}: {e}")
                    enhanced_jobs.append(job)
            
            # Add remaining jobs without enhancement
            enhanced_jobs.extend(jobs_remaining)
            logging.info(f"Enhanced {len(jobs_to_enhance)} jobs with company info, {len(jobs_remaining)} jobs added without enhancement")

        logging.info("Saving jobs to storage...")
        data_manager.save_jobs(enhanced_jobs)

        stats = data_manager.get_stats()
        logging.info("Scraping completed!")
        logging.info(f"Total jobs stored: {stats['total_jobs']}")
        logging.info(f"Unique companies: {stats['unique_companies']}")
        logging.info(f"Sources: {stats['sources']}")

        data_manager.export_to_csv("data/jobs_export.csv")
        logging.info("Data exported to CSV")

        return enhanced_jobs
    
    except Exception as e:
        logging.error(f"Scraping workflow failed: {e}")
        return []
    
    finally:
        company_extractor.cleanup()


def search_existing_jobs():
    """Search existing jobs from JSON data"""
    data_manager = JobDataManager("data/jobs.json")
    filters = {
        'location': 'remote',
        'title': 'python'
    }

    filtered_jobs = data_manager.filter_jobs(filters)
    print(f"Found {len(filtered_jobs)} remote Python jobs")

    for job in filtered_jobs[:5]:
        print(f"- {job.get('title')} at {job.get('company')} ({job.get('location')})")


# Convenience functions for different use cases
def scrape_jobs(job_title, location, sources=['indeed'], max_jobs=25, use_django=None):
    """
    Main scraper function that chooses between Django and standalone mode
    
    Args:
        job_title: Job title to search for
        location: Location to search in
        sources: List of sources to scrape
        max_jobs: Maximum number of jobs per source
        use_django: Force Django mode (True), standalone mode (False), or auto-detect (None)
    """
    if use_django is None:
        use_django = DJANGO_AVAILABLE and run_scraper_task is not None
    
    if use_django:
        logging.info("Running in Django mode (database storage)")
        return run_django_scraper(job_title, location, sources, max_jobs)
    else:
        logging.info("Running in standalone mode (JSON file storage)")
        if len(sources) > 1:
            logging.warning("Standalone mode doesn't support multiple sources efficiently. Using Indeed only.")
        return run_standalone_scraper(job_title, location, max_jobs)


if __name__ == '__main__':
    """
    Script execution entry point
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Job Scraper')
    parser.add_argument('--title', default='Python Developer', help='Job title to search for')
    parser.add_argument('--location', default='Remote', help='Location to search in')
    parser.add_argument('--sources', nargs='+', default=['indeed'], choices=['indeed', 'glassdoor'], help='Sources to scrape')
    parser.add_argument('--max-jobs', type=int, default=25, help='Maximum jobs per source')
    parser.add_argument('--mode', choices=['django', 'standalone', 'auto'], default='auto', help='Execution mode')
    parser.add_argument('--search', action='store_true', help='Search existing jobs instead of scraping')
    
    args = parser.parse_args()
    
    if args.search:
        search_existing_jobs()
    else:
        use_django = {
            'django': True,
            'standalone': False,
            'auto': None
        }[args.mode]
        
        print(f"Starting scraper for '{args.title}' in '{args.location}'")
        print(f"Sources: {', '.join(args.sources)}")
        print(f"Max jobs per source: {args.max_jobs}")
        print(f"Mode: {args.mode}")
        print("-" * 50)
        
        results = scrape_jobs(
            job_title=args.title,
            location=args.location,
            sources=args.sources,
            max_jobs=args.max_jobs,
            use_django=use_django
        )
        
        if results:
            print(f"\nScraping completed! Check the output above for details.")
        else:
            print(f"\nScraping failed or returned no results.")