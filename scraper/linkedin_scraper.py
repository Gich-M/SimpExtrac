import re
import logging
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import urlparse

try:
    import hrequests
    HREQUESTS_AVAILABLE = True
    logging.info("hrequests library available")
except ImportError:
    HREQUESTS_AVAILABLE = False
    logging.warning("hrequests not available, falling back to requests")

try:
    import requests
except ImportError:
    requests = None
    logging.error("requests library not available")

from .base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """
    Optimized LinkedIn job scraper with only working selectors.
    
    Uses Selenium for navigation and hrequests/requests for descriptions.
    Tested and verified selectors based on actual usage patterns.
    """
    
    def __init__(self, fetch_descriptions=True):
        super().__init__()
        self.valid_domains = ['www.linkedin.com', 'linkedin.com']
        self.wait = None
        self.hrequests_session = None
        self.fetch_descriptions = fetch_descriptions

        # Initialize HTTP client for descriptions
        if HREQUESTS_AVAILABLE and self.fetch_descriptions:
            try:
                self.hrequests_session = hrequests.Session()
                logging.info("LinkedIn scraper: hrequests session initialized")
            except Exception as e:
                logging.warning(f"LinkedIn scraper: Failed to initialize hrequests session: {e}")
                self.hrequests_session = None
        
        if not self.hrequests_session and requests:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
        else:
            self.session = None

    def setup_driver(self):
        driver = super().setup_driver()
        if driver:
            self.wait = WebDriverWait(driver, 10)
        return driver

    def _validate_url(self, url):
        """Validate that URL is appropriate for LinkedIn scraper"""
        try:
            parsed = urlparse(url)
            return (parsed.netloc in self.valid_domains and 
                    '/jobs/' in parsed.path)
        except:
            return False

    def navigate_to_url(self, url):
        """Navigate to LinkedIn jobs page and handle sign-in modal"""
        if not self._validate_url(url):
            logging.error(f"Invalid LinkedIn URL: {url}")
            return False

        try:
            logging.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Handle sign-in modal if present
            self._dismiss_signin_modal()
            
            # Wait for job cards to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.base-search-card'))
            )
            logging.info("LinkedIn page loaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False

    def _dismiss_signin_modal(self):
        """Dismiss LinkedIn sign-in modal if present"""
        try:
            # Working modal dismiss selector
            dismiss_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                'button.contextual-sign-in-modal__modal-dismiss'
            )
            dismiss_button.click()
            logging.info("Sign-in modal dismissed")
        except:
            logging.debug("No sign-in modal found or already dismissed")

    def get_page_source_for_parsing(self):
        """Get page source for BeautifulSoup parsing"""
        return self.driver.page_source

    def extract_job_cards(self, html_content):
        """Extract job cards from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.select('.base-search-card')
        logging.info(f"Found {len(job_cards)} job cards")
        return job_cards

    def _clean_location_text(self, location_text):
        """Clean location text by removing timestamps and extra spaces"""
        if not location_text:
            return "N/A"
        
        # Remove common timestamp patterns
        cleaned = re.sub(r'\b\d+\s+(hours?|minutes?|days?|weeks?|months?)\s+ago\b', '', location_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = re.sub(r',\s*$', '', cleaned)
        
        return cleaned if cleaned else "N/A"

    def extract_job_details(self, job_card):
        """Extract job details using only verified working selectors"""
        try:
            # Extract URL and title from anchor tag
            link_elem = job_card.select_one('a[href*="/jobs/view/"]')
            if not link_elem:
                logging.error("NO JOB URL/TITLE FOUND - SKIPPING JOB")
                return None
            
            job_url = link_elem.get('href', '')
            title_text = link_elem.get_text(strip=True)
            
            if job_url and not job_url.startswith('http'):
                job_url = 'https://www.linkedin.com' + job_url
                            
            # Extract company
            company = "N/A"
            company_elem = job_card.select_one('.base-search-card__subtitle')
            if company_elem:
                company = company_elem.get_text(strip=True)
            
            # Extract location
            location = "N/A"
            location_elem = job_card.select_one('.base-search-card__metadata span:first-child')
            if location_elem:
                raw_location = location_elem.get_text(strip=True)
                location = self._clean_location_text(raw_location)
            
            # Get description if enabled
            description = "Description fetching disabled"
            if self.fetch_descriptions and job_url:
                description = self.fetch_job_description(job_url)
            
            return {
                'title': title_text,
                'company': company,
                'location': location,
                'description': description,
                'url': job_url,
                'source': 'LinkedIn'
            }
            
        except Exception as e:
            logging.error(f"Error extracting job details: {e}")
            return None

    def _clean_description_text(self, desc_elem):
        """Clean and format job description text"""
        if not desc_elem:
            return "Description not available"
        
        # Remove HTML comments
        html_content = str(desc_elem)
        html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
        
        # Parse and clean
        cleaned_soup = BeautifulSoup(html_content, 'html.parser')
        description = cleaned_soup.get_text(separator=' ', strip=True)
        description = re.sub(r'\s+', ' ', description)
        description = re.sub(r'Show more\s*Show less', '', description, flags=re.IGNORECASE)
        description = description.strip()
        
        return description if description else "Description not available"

    def fetch_job_description(self, job_url):
        """Fetch job description using single working selector"""
        if not job_url or not self.fetch_descriptions:
            return "Description fetching disabled"
        
        try:
            # Use hrequests or requests
            if self.hrequests_session:
                response = self.hrequests_session.get(job_url, timeout=10)
            elif self.session:
                response = self.session.get(job_url, timeout=10)
            else:
                return "Description fetching not available - no HTTP client"
            
            if response.status_code != 200:
                return "Description not available"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            desc_elem = soup.select_one('.show-more-less-html__markup')
            if desc_elem:
                description = self._clean_description_text(desc_elem)
                if len(description) > 50:
                    if len(description) > 3000:
                        description = description[:3000] + "... [truncated]"
                    return description
            
            return "Description not available"
                
        except Exception as e:
            logging.error(f"Description fetch error: {str(e)[:100]}")
            return "Description not available"

    def scrape_jobs(self, filtered_url, num_jobs):
        """
        Main scraping method
        
        Args:
            filtered_url (str): LinkedIn jobs URL with filters
            num_jobs (int): Number of jobs to scrape
            
        Returns:
            list: List of job dictionaries
        """
        jobs = []

        try:
            logging.info(f"Starting LinkedIn scraping: {num_jobs} jobs from URL")
            
            # Initialize driver
            self.driver = self.setup_driver()
            if not self.driver:
                logging.error("Failed to setup driver")
                return []
            
            if not self.navigate_to_url(filtered_url):
                return []
            
            html_content = self.get_page_source_for_parsing()
            job_cards = self.extract_job_cards(html_content)

            if not job_cards:
                logging.warning("No job cards found")
                return []

            # Extract job details from each card
            for card in job_cards:
                if len(jobs) >= num_jobs:
                    break

                job_data = self.extract_job_details(card)
                if job_data:
                    jobs.append(job_data)
                    logging.info(f"Extracted: {job_data['title']} at {job_data['company']}")
        
        except Exception as e:
            logging.error(f"Scraping error: {e}")
        finally:
            self.quit_driver()

        logging.info(f"LinkedIn scraping completed: {len(jobs)} jobs extracted")
        return jobs