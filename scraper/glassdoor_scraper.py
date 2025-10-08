from .base_scraper import BaseScraper
from bs4 import BeautifulSoup
import requests
import time
import logging
import re
import random
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

try:
    import hrequests
    HREQUESTS_AVAILABLE = True
except ImportError:
    HREQUESTS_AVAILABLE = False

class GlassdoorScraper(BaseScraper):
    """
    Glassdoor job scraper.
    
    Uses Selenium for main scraping and requests for job descriptions.
    URL-based input, job data extraction.
    Extracts: title, company, location, description, URL.
    """
    
    def __init__(self, fetch_descriptions=True):
        super().__init__()
        self.valid_domains = ['www.glassdoor.com', 'glassdoor.com']
        self.wait = None
        self.session = requests.Session()
        self.fetch_descriptions = fetch_descriptions

        # Setup hrequests session if available
        if HREQUESTS_AVAILABLE:
            self.hrequests_session = hrequests.Session(browser='chrome')
            logging.info("Using hrequests session for description fetching")
        else:
            self.hrequests_session = None
            logging.warning("hrequests not available, description fetching will be disabled")

        # Headers for requests
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

    def setup_driver(self):
        driver = super().setup_driver()
        if driver:
            self.wait = WebDriverWait(driver, 10)
        return driver

    def _validate_url(self, url):
        """Validate that URL is appropriate for Glassdoor scraper"""
        try:
            parsed = urlparse(url)
            # Check if it's a Glassdoor domain
            if parsed.netloc not in self.valid_domains:
                return False
            # Check if it's a jobs search URL
            if '/Job/' not in parsed.path and 'jobs' not in parsed.path.lower():
                return False
            return True
        except Exception:
            return False

    def navigate_to_url(self, filtered_url):
        """Navigate to user-provided filtered URL using Selenium"""
        try:
            if not self._validate_url(filtered_url):
                raise ValueError(f"Invalid Glassdoor URL: {filtered_url}")
                
            logging.info(f"Navigating to filtered Glassdoor URL: {filtered_url}")
            
            if not self.setup_driver():
                return False
                
            self.driver.get(filtered_url)
            time.sleep(random.uniform(3, 5))  # Wait for page load
            
            # Check for job results on the page
            if self.driver.find_elements(By.CSS_SELECTOR, "[data-jobid]"):
                logging.info("Job listings found")
                return True
            else:
                logging.warning("No job results found")
                return False
            
        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False

    def get_page_source_for_parsing(self):
        """Get page source from Selenium driver for BeautifulSoup4 parsing"""
        return self.driver.page_source if self.driver else ""
    
    def extract_job_cards(self, html_content):
        """Extract job cards using BeautifulSoup4"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.select('li[data-jobid]')
        
        if not job_cards:
            # Fallback to any job links
            job_cards = soup.find_all('a', href=lambda x: x and '/job/' in x)

        logging.info(f"Found {len(job_cards)} job cards")
        return job_cards
    
    def extract_job_details(self, job_card):
        """Extract job details from job card"""
        try:
            # Extract title and URL
            title_elem = job_card.select_one('a[data-test="job-title"]')
            
            if title_elem:
                title = title_elem.get_text(strip=True)
                job_url = title_elem.get('href', '')
            else:
                return None
            
            # Make URL absolute
            if job_url and not job_url.startswith('http'):
                job_url = 'https://www.glassdoor.com' + job_url
            
            # Extract company name
            company = "N/A"
            company_elem = job_card.select_one('span[class*="EmployerProfile_compactEmployerName"]')
            
            if company_elem:
                company = company_elem.get_text(strip=True)

            # Extract location
            location = "N/A"
            location_elem = job_card.select_one('div[class*="location"]')
            
            if location_elem:
                location = location_elem.get_text(strip=True)

            return {
                'title': title,
                'company': company,
                'location': location,
                'url': job_url,
                'description': (self.fetch_job_description(job_url)
                              if job_url and self.fetch_descriptions
                              else "Description fetching disabled"),
                'source': 'Glassdoor'
            }
        except Exception as e:
            logging.error(f"Error extracting job details: {e}")
            return None

    def _clean_job_description(self, description):
        """
        Clean job description text.
        
        Args:
            description (str): Raw description text
            
        Returns:
            str: Cleaned description
        """
        if not description:
            return "N/A"
            
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', description.strip())
        
        # Remove common unwanted patterns
        cleaned = re.sub(r'\n+', ' ', cleaned)
        cleaned = re.sub(r'\t+', ' ', cleaned)
        
        return cleaned

    def fetch_job_description(self, job_url):
        """Fetch job description using hrequests if available, fallback to requests"""
        try:
            # Check if hrequests is available
            if not self.hrequests_session:
                logging.warning("hrequests session not available, skipping description fetch")
                return "Description not available (hrequests not installed)"
                
            resp = self.hrequests_session.get(
                job_url,
                timeout=10,  # Reduced timeout to avoid hanging
                headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                }
            )
            
            if resp.status_code != 200:
                return "Description not available"
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Use proven working selector
            desc_elem = soup.select_one('div[class*="JobDetails_jobDescription"]')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                if len(description) > 50:
                    # Clean and limit length
                    description = re.sub(r'\s+', ' ', description)
                    description = self._clean_job_description(description)
                    
                    if len(description) > 3000:
                        description = description[:3000] + "... [truncated]"
                    
                    return description
            
            return "Description not available"
                
        except Exception as e:
            logging.error(f"Error fetching description: {str(e)[:100]}")
            return "Description not available"
        
    def scrape_jobs(self, filtered_url, num_jobs):
        """
        Main scraping method - accepts pre-filtered URL from user
        
        Args:
            filtered_url (str): Pre-filtered Glassdoor jobs URL (e.g., 'https://www.glassdoor.com/Job/jobs.htm?sc.keyword=software+engineer&locT=N')
            num_jobs (int): Number of jobs to scrape (required, specified by user)
            
        Returns:
            list: List of job dictionaries
        """
        jobs = []

        try:
            if not self.navigate_to_url(filtered_url):
                return []
            
            html_content = self.get_page_source_for_parsing()
            job_cards = self.extract_job_cards(html_content)

            if not job_cards:
                return []

            for card in job_cards:
                if len(jobs) >= num_jobs:
                    break

                job_data = self.extract_job_details(card)
                if job_data:
                    jobs.append(job_data)
        
        except Exception as e:
            logging.error(f"Scraping error: {e}")
        finally:
            self.quit_driver()

        return jobs[:num_jobs]

