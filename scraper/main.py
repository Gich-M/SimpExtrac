"""
Main scraper orchestrator - URL-based job scraping

Requirements Implementation:
- User provides filtered URL + number of jobs to scrape
- Auto-detects source (Indeed/Glassdoor/LinkedIn) from URL
- Scrapes all requested jobs with full details
- Enhances ALL jobs with company website and email extraction
- Saves to Django model with duplicate handling
- Returns comprehensive results
"""
import sys
import os
import logging

# Add the project root to the Python path for standalone execution
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup for when running as script
def setup_django():
    """Setup Django environment if not already configured"""
    try:
        import django
        from django.conf import settings
        
        if not settings.configured:
            # Set the Django settings module
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SimpExtrac.settings')
            
            # Setup Django
            django.setup()
            
            # Verify setup worked
            from django.db import connection
            connection.ensure_connection()
            
        return True
    except Exception as e:
        print(f"Django setup failed: {e}")
        return False

# Check if Django is available
DJANGO_AVAILABLE = setup_django()

# Import components
try:
    from .tasks import run_scraper_url_task
except ImportError:
    try:
        from tasks import run_scraper_url_task
    except ImportError:
        run_scraper_url_task = None


def scrape_jobs_url(filtered_url, num_jobs=25):
    """
    Main job scraping function - orchestrates the entire process
    
    Args:
        filtered_url (str): Pre-filtered job search URL from Indeed/Glassdoor/LinkedIn
        num_jobs (int): Number of jobs to scrape (default only for CLI usage)
        
    Returns:
        dict: Scraping results with job count, companies, and details
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if DJANGO_AVAILABLE and run_scraper_url_task:
        # Use Django task system (preferred mode)
        logging.info("Running job scraping in Django mode")
        return run_scraper_url_task(filtered_url, num_jobs)
    else:
        # Django not available
        logging.error("Django not available. This scraper requires Django integration.")
        raise RuntimeError("Django integration required. Please ensure Django is properly configured.")


if __name__ == '__main__':
    """
    Command line interface for job scraping
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Job Scraper - URL-based scraping tool')
    parser.add_argument('filtered_url', help='Pre-filtered URL from Indeed, Glassdoor, or LinkedIn')
    parser.add_argument('--num-jobs', type=int, default=25, help='Number of jobs to scrape (default: 25)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Job Scraper - URL-based scraping")
    print("=" * 60)
    print(f"Filtered URL: {args.filtered_url}")
    print(f"Jobs to Scrape: {args.num_jobs}")
    print("-" * 60)
    
    try:
        results = scrape_jobs_url(args.filtered_url, args.num_jobs)
        
        print("\n" + "=" * 60)
        print("SCRAPING RESULTS")
        print("=" * 60)
        print(f"Source: {results['source']}")
        print(f"Jobs Found: {results.get('total_scraped', 0)}")
        print(f"Jobs Saved: {results['jobs_saved']}")
        print(f"Companies: {results['companies_created']}")
        print(f"Scraping Time: {results.get('scraping_time', 0):.2f}s")
        
        if results.get('errors'):
            print(f"Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"  - {error}")
        
        print("=" * 60)
        print("Scraping completed successfully!")
        
    except Exception as e:
        print(f"\nScraping failed: {e}")
        sys.exit(1)