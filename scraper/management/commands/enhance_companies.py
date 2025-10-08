#!/usr/bin/env python3
"""
Standalone Company Info Enhancement Script

This script reads jobs from jobs.json and enhances them with company websites and emails
using the CompanyInfoExtractor. It's designed for independent testing of requirements 8-9.

Usage:
    python enhance_companies.py [--input jobs.json] [--output enhanced_jobs.json] [--limit 5]
"""

import json
import os
import sys
import time
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('company_enhancement.log')
    ]
)

def setup_django():
    """Setup Django environment for model access"""
    try:
        import django
        from django.conf import settings
        
        if not settings.configured:
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SimpExtrac.settings')
            django.setup()
        return True
    except Exception as e:
        logging.warning(f"Django setup failed: {e}")
        return False

# Try to setup Django (optional for this script)
DJANGO_AVAILABLE = setup_django()

try:
    from scraper.company_info_extractor import CompanyInfoExtractor
except ImportError:
    logging.error("Could not import CompanyInfoExtractor. Make sure you're in the right directory.")
    sys.exit(1)


class CompanyEnhancer:
    """
    Standalone company information enhancer
    """
    
    def __init__(self):
        self.extractor = CompanyInfoExtractor()
        self.results = {
            'total_jobs': 0,
            'processed': 0,
            'enhanced_with_website': 0,
            'enhanced_with_email': 0,
            'fully_enhanced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
    
    def load_jobs_from_json(self, json_file_path):
        """Load jobs from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            jobs = data.get('jobs', [])
            self.results['total_jobs'] = len(jobs)
            
            logging.info(f"✅ Loaded {len(jobs)} jobs from {json_file_path}")
            return jobs
            
        except FileNotFoundError:
            logging.error(f"❌ File not found: {json_file_path}")
            return []
        except json.JSONDecodeError as e:
            logging.error(f"❌ Invalid JSON in {json_file_path}: {e}")
            return []
        except Exception as e:
            logging.error(f"❌ Error loading {json_file_path}: {e}")
            return []
    
    def enhance_job(self, job_data):
        """
        Enhance a single job with company website and email
        
        Args:
            job_data (dict): Job data from JSON
            
        Returns:
            dict: Enhanced job data
        """
        company_name = None
        
        # Extract company name (handle both formats)
        if isinstance(job_data.get('company'), dict):
            company_name = job_data['company'].get('name')
        elif isinstance(job_data.get('company'), str):
            company_name = job_data['company']
        
        if not company_name or company_name.lower() in ['n/a', 'unknown', '']:
            logging.warning(f"⚠️  Skipping job with invalid company: {company_name}")
            self.results['skipped'] += 1
            return job_data
        
        logging.info(f"🔍 Processing: {job_data.get('title', 'Unknown Title')} at {company_name}")
        
        try:
            # Search for company website
            logging.info(f"   🌐 Searching for website: {company_name}")
            website = self.extractor.search_company_website(company_name)
            
            # Update job data structure
            if isinstance(job_data.get('company'), dict):
                job_data['company']['website'] = website
            else:
                # Convert string company to dict format
                job_data['company'] = {
                    'name': company_name,
                    'website': website,
                    'email': None
                }
            
            email = None
            if website:
                logging.info(f"   ✅ Found website: {website}")
                self.results['enhanced_with_website'] += 1
                
                # Extract email from website
                logging.info(f"   📧 Searching for email on: {website}")
                time.sleep(2)  # Be respectful to websites
                email = self.extractor.extract_company_email(website)
                
                if email:
                    logging.info(f"   ✅ Found email: {email}")
                    job_data['company']['email'] = email
                    self.results['enhanced_with_email'] += 1
                else:
                    logging.warning(f"   ⚠️  No email found on {website}")
            else:
                logging.warning(f"   ⚠️  No website found for {company_name}")
            
            # Track full enhancement
            if website and email:
                self.results['fully_enhanced'] += 1
                logging.info(f"   🎉 Fully enhanced: {company_name}")
            
            self.results['processed'] += 1
            return job_data
            
        except Exception as e:
            error_msg = f"Error enhancing {company_name}: {str(e)}"
            logging.error(f"   ❌ {error_msg}")
            self.results['errors'].append(error_msg)
            self.results['failed'] += 1
            return job_data
    
    def enhance_all_jobs(self, jobs, limit=None):
        """
        Enhance all jobs with company information
        
        Args:
            jobs (list): List of job dictionaries
            limit (int): Maximum number of jobs to process
            
        Returns:
            list: Enhanced job list
        """
        if limit:
            jobs = jobs[:limit]
            logging.info(f"🔢 Processing limited to {limit} jobs")
        
        enhanced_jobs = []
        
        logging.info(f"🚀 Starting enhancement of {len(jobs)} jobs...")
        start_time = time.time()
        
        for i, job in enumerate(jobs, 1):
            logging.info(f"\n--- Job {i}/{len(jobs)} ---")
            
            enhanced_job = self.enhance_job(job)
            enhanced_jobs.append(enhanced_job)
            
            # Progress update
            if i % 5 == 0 or i == len(jobs):
                elapsed = time.time() - start_time
                avg_time = elapsed / i
                remaining = (len(jobs) - i) * avg_time
                
                logging.info(f"📊 Progress: {i}/{len(jobs)} ({i/len(jobs)*100:.1f}%) - "
                           f"Elapsed: {elapsed:.1f}s - Remaining: {remaining:.1f}s")
            
            # Be respectful with delays
            if i < len(jobs):
                time.sleep(3)  # 3 second delay between companies
        
        total_time = time.time() - start_time
        logging.info(f"⏱️  Total processing time: {total_time:.1f} seconds")
        
        return enhanced_jobs
    
    def save_enhanced_jobs(self, enhanced_jobs, original_data, output_file):
        """Save enhanced jobs to JSON file"""
        try:
            # Create enhanced data structure
            enhanced_data = {
                'export_info': original_data.get('export_info', {}),
                'enhancement_info': {
                    'enhanced_at': time.strftime('%Y-%m-%dT%H:%M:%S+00:00'),
                    'enhancement_results': self.results
                },
                'jobs': enhanced_jobs
            }
            
            # Update export info
            enhanced_data['export_info']['enhanced'] = True
            enhanced_data['export_info']['total_jobs'] = len(enhanced_jobs)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"✅ Enhanced jobs saved to: {output_file}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error saving enhanced jobs: {e}")
            return False
    
    def print_summary(self):
        """Print enhancement summary"""
        print("\n" + "="*80)
        print("🎯 COMPANY ENHANCEMENT RESULTS")
        print("="*80)
        print(f"📊 Total jobs processed: {self.results['processed']}/{self.results['total_jobs']}")
        print(f"🌐 Enhanced with website: {self.results['enhanced_with_website']}")
        print(f"📧 Enhanced with email: {self.results['enhanced_with_email']}")
        print(f"🎉 Fully enhanced (website + email): {self.results['fully_enhanced']}")
        print(f"⚠️  Skipped (invalid company): {self.results['skipped']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['total_jobs'] > 0:
            success_rate = (self.results['enhanced_with_website'] / self.results['total_jobs']) * 100
            full_rate = (self.results['fully_enhanced'] / self.results['total_jobs']) * 100
            print(f"📈 Website success rate: {success_rate:.1f}%")
            print(f"📈 Full enhancement rate: {full_rate:.1f}%")
        
        if self.results['errors']:
            print(f"\n❌ Errors encountered:")
            for error in self.results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(self.results['errors']) > 5:
                print(f"   ... and {len(self.results['errors']) - 5} more errors")
        
        print("="*80)
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.extractor.cleanup()
        except Exception as e:
            logging.warning(f"Cleanup error: {e}")


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhance jobs with company website and email information')
    parser.add_argument(
        '--input', 
        default='data/jobs.json',
        help='Input JSON file path (default: data/jobs.json)'
    )
    parser.add_argument(
        '--output',
        default='data/enhanced_jobs.json', 
        help='Output JSON file path (default: data/enhanced_jobs.json)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of jobs to process (for testing)'
    )
    parser.add_argument(
        '--company',
        help='Process only jobs from specific company (for testing)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        print("💡 Try: python manage.py export_jobs --output data/jobs.json --pretty")
        sys.exit(1)
    
    enhancer = CompanyEnhancer()
    
    try:
        print("🚀 Starting Company Information Enhancement")
        print("="*80)
        print(f"📁 Input file: {args.input}")
        print(f"📁 Output file: {args.output}")
        if args.limit:
            print(f"🔢 Limit: {args.limit} jobs")
        if args.company:
            print(f"🏢 Company filter: {args.company}")
        print("="*80)
        
        # Load jobs
        print("\n📖 Loading jobs from JSON...")
        with open(args.input, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        jobs = original_data.get('jobs', [])
        
        # Filter by company if specified
        if args.company:
            original_count = len(jobs)
            jobs = [job for job in jobs 
                   if args.company.lower() in str(job.get('company', '')).lower()]
            print(f"🔍 Filtered to {len(jobs)} jobs (from {original_count}) matching '{args.company}'")
        
        if not jobs:
            print("❌ No jobs found to process")
            sys.exit(1)
        
        # Enhance jobs
        enhanced_jobs = enhancer.enhance_all_jobs(jobs, limit=args.limit)
        
        # Save results
        print(f"\n💾 Saving enhanced jobs to {args.output}...")
        success = enhancer.save_enhanced_jobs(enhanced_jobs, original_data, args.output)
        
        if success:
            # Print summary
            enhancer.print_summary()
            
            print(f"\n🎉 Enhancement complete!")
            print(f"📄 Enhanced data saved to: {args.output}")
            print(f"📋 Log file: company_enhancement.log")
        else:
            print("❌ Failed to save enhanced jobs")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Enhancement interrupted by user")
    except Exception as e:
        print(f"\n❌ Enhancement failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        enhancer.cleanup()


if __name__ == '__main__':
    main()