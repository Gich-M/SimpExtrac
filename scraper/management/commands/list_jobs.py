"""
Django management command to list saved jobs
"""
from django.core.management.base import BaseCommand
from jobs.models import Job, Company
from django.utils import timezone
from django.db import models
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'List saved jobs with filtering options'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Filter by source (indeed, glassdoor, linkedin)',
        )
        parser.add_argument(
            '--company',
            type=str,
            help='Filter by company name (partial match)',
        )
        parser.add_argument(
            '--location',
            type=str,
            help='Filter by location (partial match)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Limit number of results (default: 20)',
        )
        parser.add_argument(
            '--recent',
            type=int,
            help='Show jobs from last N days',
        )
        parser.add_argument(
            '--show-description',
            action='store_true',
            help='Show job descriptions (truncated)',
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show statistics only',
        )

    def handle(self, *args, **options):
        # Build query
        jobs = Job.objects.select_related('company').all()
        
        # Apply filters
        if options['source']:
            jobs = jobs.filter(source__icontains=options['source'])
        
        if options['company']:
            jobs = jobs.filter(company__name__icontains=options['company'])
            
        if options['location']:
            jobs = jobs.filter(location__icontains=options['location'])
            
        if options['recent']:
            days_ago = timezone.now() - timedelta(days=options['recent'])
            jobs = jobs.filter(scraped_at__gte=days_ago)
        
        # Order by most recent
        jobs = jobs.order_by('-scraped_at')
        
        # Show statistics if requested
        if options['stats']:
            self.show_stats(jobs)
            return
        
        # Limit results
        total_count = jobs.count()
        jobs = jobs[:options['limit']]
        
        # Display header
        self.stdout.write("=" * 80)
        self.stdout.write("SAVED JOBS")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Showing {len(jobs)} of {total_count} jobs")
        self.stdout.write("-" * 80)
        
        # Display jobs
        for i, job in enumerate(jobs, 1):
            self.stdout.write(f"\n{i}. {self.style.SUCCESS(job.title)}")
            self.stdout.write(f"   Company: {job.company.name}")
            self.stdout.write(f"   Location: {job.location}")
            self.stdout.write(f"   Source: {job.source}")
            self.stdout.write(f"   Scraped: {job.scraped_at.strftime('%Y-%m-%d %H:%M')}")
            
            if job.company.company_website:
                self.stdout.write(f"   Website: {job.company.company_website}")
            if job.company.company_email:
                self.stdout.write(f"   Email: {job.company.company_email}")
            
            if options['show_description'] and job.description:
                desc = job.description[:200] + "..." if len(job.description) > 200 else job.description
                self.stdout.write(f"   Description: {desc}")
            
            if job.url:
                self.stdout.write(f"   URL: {job.url}")
        
        self.stdout.write("\n" + "=" * 80)
        
        if total_count > options['limit']:
            self.stdout.write(f"Use --limit {total_count} to see all jobs")
    
    def show_stats(self, jobs):
        """Show job statistics"""
        total_jobs = jobs.count()
        
        # Source breakdown
        sources = jobs.values('source').distinct()
        source_counts = {s['source']: jobs.filter(source=s['source']).count() for s in sources}
        
        # Company breakdown
        companies = jobs.values('company__name').distinct()
        company_counts = {c['company__name']: jobs.filter(company__name=c['company__name']).count() 
                         for c in companies}
        top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Recent activity
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        today_jobs = jobs.filter(scraped_at__date=today).count()
        yesterday_jobs = jobs.filter(scraped_at__date=yesterday).count()
        week_jobs = jobs.filter(scraped_at__gte=week_ago).count()
        
        # Enhanced jobs count (jobs that have either website OR email)
        enhanced_jobs = jobs.filter(
            (models.Q(company__company_website__isnull=False) & ~models.Q(company__company_website__exact='')) |
            (models.Q(company__company_email__isnull=False) & ~models.Q(company__company_email__exact=''))
        ).count()
        
        # Display statistics
        self.stdout.write("=" * 80)
        self.stdout.write("JOB STATISTICS")
        self.stdout.write("=" * 80)
        
        self.stdout.write(f"Total Jobs: {total_jobs}")
        self.stdout.write(f"Enhanced with Company Info: {enhanced_jobs}")
        self.stdout.write(f"Enhancement Rate: {(enhanced_jobs/total_jobs*100):.1f}%" if total_jobs > 0 else "Enhancement Rate: 0%")
        
        self.stdout.write("\nRecent Activity:")
        self.stdout.write(f"  Today: {today_jobs}")
        self.stdout.write(f"  Yesterday: {yesterday_jobs}")
        self.stdout.write(f"  Last 7 days: {week_jobs}")
        
        self.stdout.write("\nBy Source:")
        for source, count in source_counts.items():
            self.stdout.write(f"  {source}: {count}")
        
        self.stdout.write("\nTop Companies:")
        for company, count in top_companies:
            self.stdout.write(f"  {company}: {count} jobs")
        
        self.stdout.write("=" * 80)