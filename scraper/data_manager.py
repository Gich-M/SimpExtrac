import json
import csv
import os
from datetime import datetime
from difflib import SequenceMatcher
from collections import Counter
import logging
from typing import List, Dict, Optional

# Django setup
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
    def __init__(self, storage_path="data/scraped_jobs.json"):
        self.storage_path = storage_path
        self.storage_dir = os.path.dirname(storage_path)

        if self.storage_dir and not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

        self.title_similarity_threshold = 0.8
        self.company_similarity_threshold = 0.9
        self.location_similarity_threshold = 0.7

    def save_jobs(self, jobs_list: List[Dict], append_mode=True):
        try:
            # Save to JSON (existing functionality)
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
        companies_created = 0
        jobs_created = 0
        jobs_updated = 0

        for job_data in jobs_list:
            # Skip incomplete records
            if not job_data.get('title') or not job_data.get('company'):
                continue

            try:
                # Get or create company
                company_name = job_data['company']
                company, created = Company.objects.get_or_create(
                    name=company_name,
                    defaults={
                        'company_website': job_data.get('company_website'),
                        'company_email': job_data.get('company_email'),
                    }
                )

                if created:
                    companies_created += 1
                    logging.info(f"Created company: {company_name}")
                else:
                    # Update company info if we have new data
                    updated = False
                    if job_data.get('company_website') and not company.company_website:
                        company.company_website = job_data.get('company_website')
                        updated = True
                    if job_data.get('company_email') and not company.company_email:
                        company.company_email = job_data.get('company_email')
                        updated = True
                    if updated:
                        company.save()

                # Parse scraped_at datetime - FIX TIMEZONE ISSUE
                scraped_at = timezone.now()  # Use timezone-aware datetime
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
                job, created = Job.objects.update_or_create(
                    title=job_data['title'],
                    company=company,
                    url=job_data.get('url', ''),
                    defaults={
                        'location': job_data.get('location', ''),
                        'description': job_data.get('description', ''),
                        'salary': job_data.get('salary', ''),
                        'source': job_data.get('source', 'Unknown'),
                        'scraped_at': scraped_at,
                    }
                )
                
                if created:
                    jobs_created += 1
                else:
                    jobs_updated += 1

            except Exception as e:
                logging.error(f'Error saving job to database: {job_data.get("title", "Unknown")} - {str(e)}')
                continue

        logging.info(f'Database save completed: {companies_created} companies created, {jobs_created} jobs created, {jobs_updated} jobs updated')

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

    def _find_duplicate(self, new_job: Dict, existing_jobs: Dict) -> Optional[int]:
        new_url = new_job.get('url', '').strip()

        for i, existing_job in enumerate(existing_jobs):
            existing_url = existing_job.get('url', '').strip()

            if new_url and existing_url and new_url == existing_url:
                return i
            
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
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
        
    def export_to_csv(self, output_path: str = None):
        if not output_path:
            output_path = self.storage_path.replace('.json', '.csv')

        jobs = self.load_jobs()
        temp_manager = JobDataManager(output_path)
        temp_manager._save_to_csv(jobs)

        logging.info(f"Exported {len(jobs)} jobs to {output_path}")

    def filter_jobs(self, filters: Dict) -> List[Dict]:
        jobs = self.load_jobs()
        filtered_jobs = []

        for job in jobs:
            match = True
            
            if 'company' in filters:
                if filters['company'].lower() not in job.get('company', '').lower():
                    match = False
            
            if 'location' in filters:
                if filters['location'].lower() not in job.get('location', '').lower():
                    match = False

            if 'title' in filters:
                if filters['title'].lower() not in job.get('title', '').lower():
                    match = False

            if 'source' in filters:
                job_sources = job.get('source', [job.get('source', '')])
                if not any(filters['source'].lower() in source.lower() for source in job_sources):
                    match = False

            if match:
                filtered_jobs.append(job)

        return filtered_jobs
    
    def cleanup_old_jobs(self, days_old: int = 30):
        jobs = self.load_jobs()
        current_time = datetime.now()

        fresh_jobs = []
        for job in jobs:
            scraped_at = job.get('scraped_at')
            if scraped_at:
                try:
                    scraped_time = datetime.fromisoformat(scraped_at)
                    age_days = (current_time - scraped_time).days

                    if age_days <= days_old:
                        fresh_jobs.append(job)
                except ValueError:
                    fresh_jobs.append(job)
            else:
                fresh_jobs.append(job)
        
        self._save_to_file(fresh_jobs)
        removed_count = len(jobs) - len(fresh_jobs)
        logging.info(f"Removed {removed_count} old jobs, kept {len(fresh_jobs)} jobs")

        return removed_count
    
    def analyze_data(self):
        """Analyze job data and provide insights"""
        jobs = self.load_jobs()
        
        if not jobs:
            print("No jobs data to analyze")
            return
            
        print(f"\n📊 JOB DATA ANALYSIS")
        print("=" * 50)
        print(f"Total Jobs: {len(jobs)}")
        
        # Analyze companies
        companies = [job.get('company', 'Unknown') for job in jobs]
        company_counts = Counter(companies)
        print(f"\n🏢 TOP COMPANIES:")
        for company, count in company_counts.most_common(5):
            print(f"  • {company}: {count} jobs")
        
        # Analyze locations
        locations = [job.get('location', 'Unknown') for job in jobs]
        location_counts = Counter(locations)
        print(f"\n📍 LOCATIONS:")
        for location, count in location_counts.most_common(5):
            print(f"  • {location}: {count} jobs")
            
        # Analyze job titles
        titles = [job.get('title', 'Unknown') for job in jobs]
        print(f"\n💼 SAMPLE JOB TITLES:")
        for title in titles[:8]:
            print(f"  • {title}")
            
        # Check data quality
        has_description = sum(1 for job in jobs if job.get('description') and 'not available' not in job.get('description', '').lower())
        has_url = sum(1 for job in jobs if job.get('url'))
        
        print(f"\n📈 DATA QUALITY:")
        print(f"  • Jobs with descriptions: {has_description}/{len(jobs)} ({has_description/len(jobs)*100:.1f}%)")
        print(f"  • Jobs with URLs: {has_url}/{len(jobs)} ({has_url/len(jobs)*100:.1f}%)")
    
    def search_jobs(self, query: str) -> List[Dict]:
        """Search jobs by keyword across title, company, description"""
        query = query.lower()
        results = []
        jobs = self.load_jobs()
        
        for job in jobs:
            searchable_text = ' '.join([
                job.get('title', ''),
                job.get('company', ''),
                job.get('description', ''),
                job.get('location', '')
            ]).lower()
            
            if query in searchable_text:
                results.append(job)
        
        return results