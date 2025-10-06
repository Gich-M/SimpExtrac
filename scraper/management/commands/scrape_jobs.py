"""
Django management command to run scraper
Usage: python manage.py scrape_jobs --title "Python Developer" --location "Remote" --source indeed --max-jobs 25
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from scraper.tasks import run_scraper_task
import logging


class Command(BaseCommand):
    help = 'Run job scraper with specified parameters'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--title',
            type=str,
            required=True,
            help='Job title to search for'
        )
        parser.add_argument(
            '--location',
            type=str,
            default='',
            help='Location to search in (optional)'
        )
        parser.add_argument(
            '--source',
            type=str,
            choices=['indeed', 'glassdoor'],
            default='indeed',
            help='Source to scrape from'
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=25,
            help='Maximum number of jobs to scrape'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
    
    def handle(self, *args, **options):
        # Set up logging
        if options['verbose']:
            logging.basicConfig(level=logging.INFO)
        
        job_title = options['title']
        location = options['location']
        source = options['source']
        max_jobs = options['max_jobs']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting scraper: '{job_title}' in '{location}' from {source} (max: {max_jobs} jobs)"
            )
        )
        
        try:
            # Run the scraper
            result = run_scraper_task(
                job_title=job_title,
                location=location,
                source=source,
                max_jobs=max_jobs
            )
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"Scraping completed successfully!\n"
                    f"Jobs saved: {result['jobs_saved']}\n"
                    f"Companies created: {result['companies_created']}\n"
                    f"Duplicates skipped: {result.get('duplicates_skipped', 0)}\n"
                    f"Total scraped: {result['total_scraped']}\n"
                    f"Scraping time: {result.get('scraping_time', 0):.2f} seconds"
                )
            )
            
            if result['errors']:
                self.stdout.write(
                    self.style.WARNING(
                        f"Errors encountered: {len(result['errors'])}"
                    )
                )
                for error in result['errors']:
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
            
        except Exception as e:
            raise CommandError(f"Scraping failed: {str(e)}")