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
from selenium.webdriver.support import expected_conditions as EC
import hrequests


class IndeedScraper(BaseScraper):
    """
    Indeed job scraper.
    
    Uses Selenium for main scraping and requests for job descriptions.
    URL-based input, job data extraction.
    Extracts: title, company, location, description, URL.

    """
    
    def __init__(self, fetch_descriptions=True):  
        super().__init__()
        self.valid_domains = ['www.indeed.com', 'indeed.com']
        self.wait = None
        self.session = requests.Session()
        self.fetch_descriptions = fetch_descriptions
        self.hrequests_session = hrequests.Session(browser='chrome')
        

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
        """Validate that URL is appropriate for Indeed scraper"""
        try:
            parsed = urlparse(url)
            # Check if it's an Indeed domain
            if parsed.netloc not in self.valid_domains:
                return False
            # Check if it's a jobs search URL
            if '/jobs' not in parsed.path:
                return False
            return True
        except Exception:
            return False
    
    def navigate_to_url(self, filtered_url):
        """Navigate to user-provided filtered URL using Selenium"""
        try:
            if not self._validate_url(filtered_url):
                raise ValueError(f"Invalid Indeed URL: {filtered_url}")

            logging.info(f"Navigating to filtered Indeed URL: {filtered_url}")
            
            if not self.setup_driver():
                return False
                
            self.driver.get(filtered_url)
            time.sleep(random.uniform(3, 5))  # Wait for page load
            
            # Check for job results on the page
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-jk]"))
                )
                logging.info("Job listings found")
                return True
            except Exception as e:
                logging.warning(f"No job results found: {e}")
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
        
        # Primary selector
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        if not job_cards:
            # Fallback selectors
            job_cards = soup.find_all('div', {'data-jk': True}) or soup.find_all('div', class_='slider_container')

        logging.info(f"Found {len(job_cards)} job cards")
        return job_cards

    def extract_job_details(self, job_card):
        """Extract job details from job card"""
        try:
            # Extract title and URL
            title, job_url = "N/A", None
            
            title_elem = job_card.select_one('h2 a span[title]')
            if title_elem:
                title = title_elem.get('title') or title_elem.get_text(strip=True)
                link_elem = title_elem.find_parent('a')
                if link_elem and link_elem.get('href'):
                    job_url = link_elem['href']
                    # Make URL absolute
                    if not job_url.startswith('http'):
                        job_url = 'https://www.indeed.com' + job_url
            else:
                return None

            # Extract company
            company = "N/A"
            company_elem = job_card.select_one('span[data-testid="company-name"]')
            if company_elem:
                company = company_elem.get_text(strip=True)

            # Extract location
            location = "N/A"
            location_elem = job_card.select_one('div[data-testid="text-location"]')
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                # Clean location text
                if company != "N/A" and location_text.startswith(company):
                    location = location_text[len(company):].strip()
                else:
                    location = location_text

            return {
                'title': title,
                'company': company,
                'location': location,
                'url': job_url,
                'description': (self.fetch_job_description(job_url)
                              if job_url and self.fetch_descriptions 
                              else "Description fetching disabled"),
                'source': 'Indeed'
            }
        except Exception as e:
            logging.error(f"Error extracting job details: {e}")
            return None

    def fetch_job_description(self, job_url):
        """Fetch job description using hrequests if available, fallback to requests"""
        if not job_url or not self.fetch_descriptions:
            return "Description fetching disabled"
        
        try:
            # Check if hrequests is available
            if not self.hrequests_session:
                logging.warning("hrequests session not available, skipping description fetch")
                return "Description not available (hrequests not installed)"
            
            response = self.hrequests_session.get(job_url, timeout=10)
            
            if response.status_code != 200:
                logging.warning(f"HTTP {response.status_code} for {job_url}")
                return "Description not available"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Primary selector for Indeed job descriptions
            desc_elem = soup.find('div', id='jobDescriptionText')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                
                # Validate and return
                if description and len(description) > 50:
                    # Clean whitespace and limit length
                    description = re.sub(r'\s+', ' ', description)
                    
                    if len(description) > 3000:
                        description = description[:3000] + "... [truncated]"
                    
                    return description
            
            return "Description not found"
                
        except Exception as e:
            logging.error(f"Description fetch error: {str(e)[:100]}")
            return "Description not available"
    
    def scrape_jobs(self, filtered_url, num_jobs):
        """
        Main scraping method - accepts pre-filtered URL from user
        
        Args:
            filtered_url (str): Pre-filtered Indeed jobs URL e.g 'https://www.indeed.com/jobs?q=software+engineer&l=New+York%2C+NY'
            num_jobs (int): Number of jobs to scrape (required, specified by user)
            
        Returns:
            list: List of job dictionaries
        """
        jobs = []

        try:
            if not self.setup_driver():
                return []
            
            if not self.navigate_to_url(filtered_url):
                return []
            
            html_content = self.get_page_source_for_parsing()
            job_cards = self.extract_job_cards(html_content)

            if not job_cards:
                logging.warning("No job cards found")
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

