"""
Django management command to view scraper statistics
Usage: python manage.py scraper_stats --source indeed --days 7
"""
from django.core.management.base import BaseCommand
from scraper.tasks import get_scraper_stats
from scraper.models import ScraperStats
import json


class Command(BaseCommand):
    help = 'View scraper statistics and performance metrics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['indeed', 'glassdoor'],
            help='Filter by specific source'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back (default: 7)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)'
        )
    
    def handle(self, *args, **options):
        source = options['source']
        days = options['days']
        output_format = options['format']
        
        # Get statistics
        stats = get_scraper_stats(source=source, days=days)
        
        if not stats.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"No statistics found for the last {days} days"
                    + (f" for {source}" if source else "")
                )
            )
            return
        
        if output_format == 'json':
            # JSON output
            data = []
            for stat in stats:
                data.append({
                    'source': stat.source,
                    'date': stat.date.isoformat(),
                    'requests_made': stat.requests_made,
                    'successful_requests': stat.successful_requests,
                    'failed_requests': stat.failed_requests,
                    'success_rate': stat.success_rate,
                    'jobs_found': stat.jobs_found,
                    'jobs_saved': stat.jobs_saved,
                    'duplicates_skipped': stat.duplicates_skipped,
                    'average_response_time': stat.average_response_time,
                    'total_scraping_time': stat.total_scraping_time,
                    'error_count': len(stat.error_details)
                })
            
            self.stdout.write(json.dumps(data, indent=2))
            
        else:
            # Table output
            self.stdout.write(
                self.style.SUCCESS(
                    f"Scraper Statistics (Last {days} days)"
                    + (f" - {source.title()}" if source else "")
                )
            )
            self.stdout.write("-" * 80)
            
            # Header
            self.stdout.write(
                f"{'Date':<12} {'Source':<10} {'Requests':<8} {'Success%':<8} "
                f"{'Jobs':<6} {'Saved':<6} {'Dups':<6} {'Avg Time':<8}"
            )
            self.stdout.write("-" * 80)
            
            # Data rows
            for stat in stats:
                self.stdout.write(
                    f"{stat.date.strftime('%Y-%m-%d'):<12} "
                    f"{stat.source.title():<10} "
                    f"{stat.requests_made:<8} "
                    f"{stat.success_rate:<7.1f}% "
                    f"{stat.jobs_found:<6} "
                    f"{stat.jobs_saved:<6} "
                    f"{stat.duplicates_skipped:<6} "
                    f"{stat.average_response_time:<7.2f}s"
                )
            
            # Summary
            self.stdout.write("-" * 80)
            
            # Calculate totals
            total_requests = sum(s.requests_made for s in stats)
            total_successful = sum(s.successful_requests for s in stats)
            total_jobs_found = sum(s.jobs_found for s in stats)
            total_jobs_saved = sum(s.jobs_saved for s in stats)
            total_duplicates = sum(s.duplicates_skipped for s in stats)
            total_time = sum(s.total_scraping_time for s in stats)
            
            overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
            avg_time = total_time / total_successful if total_successful > 0 else 0
            
            self.stdout.write(
                f"{'TOTALS':<12} "
                f"{'ALL':<10} "
                f"{total_requests:<8} "
                f"{overall_success_rate:<7.1f}% "
                f"{total_jobs_found:<6} "
                f"{total_jobs_saved:<6} "
                f"{total_duplicates:<6} "
                f"{avg_time:<7.2f}s"
            )
            
            # Error summary
            total_errors = sum(len(s.error_details) for s in stats)
            if total_errors > 0:
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(f"Total errors in period: {total_errors}")
                )