import json
import csv
import os
from datetime import datetime
import logging
from typing import List, Dict, Optional
import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SimpExtrac.settings')
django.setup()

from jobs.models import Company, Job
from django.utils.dateparse import parse_datetime
from django.utils import timezone

class JobDataManager:
    """
    Job data manager
    - Save jobs to Django models
    - Handle duplicates and merge from multiple sources
    """
    def __init__(self, storage_path="data/scraped_jobs.json"):
        self.storage_path = storage_path
        self.storage_dir = os.path.dirname(storage_path)

        if self.storage_dir and not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_jobs(self, jobs_list: List[Dict], append_mode=True):
        try:
            # Save to JSON and CSV
            existing_jobs = []
            if append_mode and os.path.exists(self.storage_path):
                existing_jobs = self.load_jobs()

            for job in jobs_list:
                job['scraped_at'] = datetime.now().isoformat()

                duplicate_index = self._find_duplicate(job, existing_jobs)

                if duplicate_index is not None:
                    existing_jobs[duplicate_index] = self._merge_job_data(
                        existing_jobs[duplicate_index], job
                    )
                    logging.info(f"Merged duplicate job: {job.get('title', 'Unknown')}")
                else:
                    existing_jobs.append(job)
                    logging.info(f"Added new job: {job.get('title', 'Unknown')}")

            self._save_to_file(existing_jobs)
            logging.info(f"Saved {len(existing_jobs)} jobs to {self.storage_path}")
            
            # Also save to Django database
            self.save_to_django_db(jobs_list)
            
        except Exception as e:
            logging.error(f"Error saving jobs: {e}")
            raise

    def save_to_django_db(self, jobs_list: List[Dict]):
        """Save jobs to Django database"""
        logging.info("DATABASE SAVE PROCESS STARTING")
        logging.info(f"Jobs to save: {len(jobs_list)}")
        
        companies_created = 0
        jobs_created = 0
        jobs_updated = 0

        for i, job_data in enumerate(jobs_list, 1):
            logging.info(f"\n--- SAVING JOB {i}/{len(jobs_list)} ---")
            
            # Skip incomplete records
            if not job_data.get('title') or not job_data.get('company'):
                logging.warning(f"Skipping incomplete job: title='{job_data.get('title')}', company='{job_data.get('company')}'")
                continue

            try:
                # Get or create company
                company_name = job_data['company']
                company_website = job_data.get('company_website')
                company_email = job_data.get('company_email')
                
                logging.info(f"Processing company: {company_name}")
                logging.info(f"  Website: {company_website}")
                logging.info(f"  Email: {company_email}")
                
                company, created = Company.objects.get_or_create(
                    name=company_name,
                    defaults={
                        'company_website': company_website,
                        'company_email': company_email,
                    }
                )

                if created:
                    companies_created += 1
                    logging.info(f"Created new company: {company_name}")
                else:
                    logging.info(f"Found existing company: {company_name}")
                    # Update company info if we have new data
                    updated = False
                    if company_website and not company.company_website:
                        logging.info(f"  Updating website: {company_website}")
                        company.company_website = company_website
                        updated = True
                    if company_email and not company.company_email:
                        logging.info(f"  Updating email: {company_email}")
                        company.company_email = company_email
                        updated = True
                    if updated:
                        company.save()
                        logging.info(f"Updated company info for: {company_name}")

                # Parse scraped_at datetime
                scraped_at = timezone.now()
                if job_data.get('scraped_at'):
                    try:
                        # Parse and make timezone-aware
                        parsed_dt = parse_datetime(job_data['scraped_at'])
                        if parsed_dt:
                            scraped_at = timezone.make_aware(parsed_dt) if timezone.is_naive(parsed_dt) else parsed_dt
                        else:
                            scraped_at = timezone.now()
                    except:
                        scraped_at = timezone.now()
                
                # Create or update job
                job_title = job_data['title']
                job_url = job_data.get('url', '')
                job_location = job_data.get('location', '')
                job_description = job_data.get('description', '')
                
                logging.info(f"Processing job: {job_title}")
                logging.info(f"  URL: {job_url}")
                
                # Use title + company + location + description for duplicate detection
                # This provides better accuracy as same title/company/location can have different roles
                try:
                    job, created = Job.objects.update_or_create(
                        title=job_title,        
                        company=company,
                        location=job_location,
                        description=job_description,
                        defaults={
                            'source': job_data.get('source', 'Unknown'),
                            'url': job_url,  # Always update URL to latest
                            'scraped_at': scraped_at,
                        }
                    )
                except Job.MultipleObjectsReturned:
                    # Handle case where multiple jobs exist with same criteria
                    # Update the most recent one
                    job = Job.objects.filter(
                        title=job_title,
                        company=company,
                        location=job_location,
                        description=job_description
                    ).order_by('-scraped_at').first()
                    
                    if job:
                        job.source = job_data.get('source', 'Unknown')
                        job.url = job_url
                        job.scraped_at = scraped_at
                        job.save()
                        created = False
                        logging.info(f"Updated most recent duplicate job: {job_title}")
                    else:
                        logging.error(f"Failed to find job to update for: {job_title}")
                        continue
                
                if created:
                    jobs_created += 1
                    logging.info(f"Created new job: {job_title}")
                else:
                    jobs_updated += 1
                    logging.info(f"Updated existing job: {job_title}")

            except Exception as e:
                logging.error(f'Error saving job to database: {job_data.get("title", "Unknown")} - {str(e)}')
                logging.error(f"Exception type: {type(e).__name__}")
                import traceback
                logging.error(f"Traceback: {traceback.format_exc()}")
                continue

        logging.info(f'\nDATABASE SAVE COMPLETED')
        logging.info(f'Summary: {companies_created} companies created, {jobs_created} jobs created, {jobs_updated} jobs updated')

    def load_jobs(self) -> List[Dict]:
        try:
            if not os.path.exists(self.storage_path):
                return []
            
            if self.storage_path.endswith('.json'):
                return self._load_from_json()
            elif self.storage_path.endswith('.csv'):
                return self._load_from_csv()
            else:
                raise ValueError("Unsupported file format. Use .json or .csv")
            
        except Exception as e:
            logging.error(f"Error loading jobs: {e}")
            return []
        
    def _load_from_json(self) -> List[Dict]:
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            return json.load(f)
        
    def _load_from_csv(self) -> List[Dict]:
        jobs = []
        with open(self.storage_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                jobs.append(row)
        
        return jobs
    
    def _save_to_file(self, jobs_list: List[Dict]):
        if self.storage_path.endswith('.json'):
            self._save_to_json(jobs_list)
        elif self.storage_path.endswith('.csv'):
            self._save_to_csv(jobs_list)
        else:
            raise ValueError("Unsupported file format")
        
    def _save_to_json(self, jobs_list: List[Dict]):
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(jobs_list, f, indent=2, ensure_ascii=False)

    def _save_to_csv(self, jobs_list: List[Dict]):
        if not jobs_list:
            return
        
        fieldnames = set()
        for job in jobs_list:
            fieldnames.update(job.keys())
        fieldnames = sorted(list(fieldnames))

        with open(self.storage_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(jobs_list)

    def _find_duplicate(self, new_job: Dict, existing_jobs: List[Dict]) -> Optional[int]:
        """
        Find duplicate job using title + company + location + description
        This matches the Django DB duplicate detection logic
        """
        new_title = new_job.get('title', '').strip()
        new_company = new_job.get('company', '').strip()
        new_location = new_job.get('location', '').strip()
        new_description = new_job.get('description', '').strip()

        for i, existing_job in enumerate(existing_jobs):
            existing_title = existing_job.get('title', '').strip()
            existing_company = existing_job.get('company', '').strip()
            existing_location = existing_job.get('location', '').strip()
            existing_description = existing_job.get('description', '').strip()

            # Check if all four key fields match
            if (new_title == existing_title and 
                new_company == existing_company and
                new_location == existing_location and
                new_description == existing_description):
                return i
            
        return None
    
    def _merge_job_data(self, existing_job: Dict, new_job: Dict) -> Dict:
        merged_job = existing_job.copy()

        existing_sources = existing_job.get('sources', [existing_job.get('source', '')])
        new_source = new_job.get('source', '')

        if new_source and new_source not in existing_sources:
            existing_sources.append(new_source)

        merged_job['sources'] = existing_sources

        for key, value in new_job.items():
            if key == 'source':
                continue

            existing_value = existing_job.get(key)

            if not existing_value or (value and len(str(value)) > len(str(existing_value))):
                merged_job[key] = value

        merged_job['last_updated'] = datetime.now().isoformat()
        
        return merged_job
    
    def get_stats(self):
        jobs = self.load_jobs()

        if not jobs:
            return {'total_jobs': 0}
        
        companies = {}
        locations = {}
        sources = {}

        for job in jobs:
            company = job.get('company', 'Unknown')
            location = job.get('location', 'Unknown')
            source = job.get('source', 'Unknown')

            companies[company] = companies.get(company, 0) + 1
            locations[location] = locations.get(location, 0) + 1
            sources[source] = sources.get(source, 0) + 1

        return {
            'total_jobs': len(jobs),
            'unique_companies': len(companies),
            'unique_locations': len(locations),
            'top_companies': sorted(companies.items(), key=lambda x: x[1], reverse=True)[:10],
            'top_locations': sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10],
            'sources': sources
        }