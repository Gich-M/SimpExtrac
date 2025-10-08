"""
Django management command for job scraping
"""
from django.core.management.base import BaseCommand, CommandError
from scraper.tasks import run_scraper_url_task


class Command(BaseCommand):
    help = 'Scrape jobs from filtered URL'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='Filtered URL from Indeed, Glassdoor, or LinkedIn')
        parser.add_argument(
            '--num-jobs',
            type=int,
            default=25,
            help='Number of jobs to scrape (default: 25)',
        )

    def handle(self, *args, **options):
        url = options['url']
        num_jobs = options['num_jobs']
        
        self.stdout.write("=" * 60)
        self.stdout.write("Job Scraper - Django Management Command")
        self.stdout.write("=" * 60)
        self.stdout.write(f"URL: {url}")
        self.stdout.write(f"Jobs to Scrape: {num_jobs}")
        self.stdout.write("-" * 60)
        
        try:
            results = run_scraper_url_task(url, num_jobs)
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("SCRAPING RESULTS")
            self.stdout.write("=" * 60)
            self.stdout.write(f"Source: {results['source']}")
            self.stdout.write(f"Jobs Found: {results.get('total_scraped', 0)}")
            self.stdout.write(f"Jobs Saved: {results['jobs_saved']}")
            self.stdout.write(f"Companies: {results['companies_created']}")
            self.stdout.write(f"Scraping Time: {results.get('scraping_time', 0):.2f}s")
            
            if results.get('errors'):
                self.stdout.write(f"Errors: {len(results['errors'])}")
                for error in results['errors']:
                    self.stdout.write(f"  - {error}")
            
            self.stdout.write("=" * 60)
            self.stdout.write(
                self.style.SUCCESS('Scraping completed successfully!')
            )
            
        except Exception as e:
            raise CommandError(f'Scraping failed: {e}')