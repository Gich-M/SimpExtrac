import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.indeed_scraper import IndeedScraper
from scraper.glassdoor_scraper import GlassdoorScraper  
from scraper.company_info_extractor import CompanyInfoExtractor
from scraper.data_manager import JobDataManager
import logging
import time

def main_scraper():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    indeed_scraper = IndeedScraper(fetch_descriptions=True)
    glassdoor_scraper = GlassdoorScraper()
    company_extractor = CompanyInfoExtractor(use_selenium=False)  # Use requests for faster processing
    data_manager = JobDataManager("data/jobs.json")

    # job_title = input("Enter the job title to search for: ")
    # location = input("Enter the job location you are looking for: ")
    job_title = "Python Developer"
    location = "Remote"
    max_jobs_per_source = 20  # Increased to get more jobs from first page

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
    data_manager = JobDataManager("data/jobs.json")
    filters = {
        'location': 'remote',
        'title': 'python'
    }

    filtered_jobs = data_manager.filter_jobs(filters)
    print(f"Found {len(filtered_jobs)} remote Python jobs")

    for job in filtered_jobs[:5]:
        print(f"- {job.get('title')} at {job.get('company')} ({job.get('location')})")

if __name__ == '__main__':
    jobs = main_scraper()

    search_existing_jobs()