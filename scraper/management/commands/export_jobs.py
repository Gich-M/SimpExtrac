"""
Django management command to export saved jobs to JSON file
"""
import json
import os
from django.core.management.base import BaseCommand
from jobs.models import Job, Company
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.serializers.json import DjangoJSONEncoder


class Command(BaseCommand):
    help = 'Export saved jobs to JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='jobs.json',
            help='Output file name (default: jobs.json)',
        )
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
            '--recent',
            type=int,
            help='Export jobs from last N days',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of jobs to export',
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty print JSON (formatted with indentation)',
        )
        parser.add_argument(
            '--minimal',
            action='store_true',
            help='Export minimal data (title, company, location, url only)',
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
        
        # Limit results if specified
        if options['limit']:
            jobs = jobs[:options['limit']]
        
        total_count = jobs.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING("No jobs found matching the criteria."))
            return
        
        # Prepare data for export
        export_data = {
            'export_info': {
                'exported_at': timezone.now().isoformat(),
                'total_jobs': total_count,
                'filters_applied': {
                    'source': options.get('source'),
                    'company': options.get('company'),
                    'location': options.get('location'),
                    'recent_days': options.get('recent'),
                    'limit': options.get('limit'),
                }
            },
            'jobs': []
        }
        
        # Convert jobs to dictionaries
        for job in jobs:
            if options['minimal']:
                job_data = {
                    'title': job.title,
                    'company': job.company.name,
                    'location': job.location,
                    'url': job.url,
                }
            else:
                job_data = {
                    'title': job.title,
                    'company': {
                        'name': job.company.name,
                        'website': job.company.company_website,
                        'email': job.company.company_email,
                    },
                    'location': job.location,
                    'url': job.url,
                    'description': job.description,
                    'source': job.source,
                    'scraped_at': job.scraped_at.isoformat(),
                    'created_at': job.created_at.isoformat(),
                    'updated_at': job.updated_at.isoformat(),
                }
            
            export_data['jobs'].append(job_data)
        
        # Determine output file path
        output_file = options['output']
        if not output_file.endswith('.json'):
            output_file += '.json'
        
        # Make path absolute if it's just a filename
        if not os.path.isabs(output_file):
            output_file = os.path.join(os.getcwd(), output_file)
        
        # Write to JSON file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if options['pretty']:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, cls=DjangoJSONEncoder)
                else:
                    json.dump(export_data, f, ensure_ascii=False, cls=DjangoJSONEncoder)
            
            # Success message
            self.stdout.write("=" * 80)
            self.stdout.write(self.style.SUCCESS("✅ JOBS EXPORTED SUCCESSFULLY"))
            self.stdout.write("=" * 80)
            self.stdout.write(f"📁 Output file: {output_file}")
            self.stdout.write(f"📊 Total jobs exported: {total_count}")
            
            # Show filters applied
            filters_applied = []
            if options['source']:
                filters_applied.append(f"source={options['source']}")
            if options['company']:
                filters_applied.append(f"company={options['company']}")
            if options['location']:
                filters_applied.append(f"location={options['location']}")
            if options['recent']:
                filters_applied.append(f"recent {options['recent']} days")
            if options['limit']:
                filters_applied.append(f"limited to {options['limit']} jobs")
            
            if filters_applied:
                self.stdout.write(f"🔍 Filters applied: {', '.join(filters_applied)}")
            
            self.stdout.write(f"💾 File size: {self._get_file_size(output_file)}")
            self.stdout.write(f"🎨 Format: {'Pretty (indented)' if options['pretty'] else 'Compact'}")
            self.stdout.write(f"📋 Data: {'Minimal' if options['minimal'] else 'Complete'}")
            self.stdout.write("=" * 80)
            
            # Show sample of first job
            if total_count > 0:
                first_job = jobs.first()
                self.stdout.write("\n📋 Sample (first job):")
                self.stdout.write(f"   Title: {first_job.title}")
                self.stdout.write(f"   Company: {first_job.company.name}")
                self.stdout.write(f"   Location: {first_job.location}")
                self.stdout.write(f"   Source: {first_job.source}")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error writing to file {output_file}: {str(e)}")
            )
            return
    
    def _get_file_size(self, file_path):
        """Get human readable file size"""
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return "Unknown"