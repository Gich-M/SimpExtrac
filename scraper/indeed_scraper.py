from .base_scraper import BaseScraper
from .cloudflare_bypass import is_cloudflare_challenge, bypass_cloudflare_challenge
from bs4 import BeautifulSoup
import requests
import hrequests
import time
import logging
import re
import random
import urllib.parse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class IndeedScraper(BaseScraper):
    def __init__(self, fetch_descriptions=True):  
        super().__init__()
        self.base_url = "https://www.indeed.com"
        self.wait = None
        self.session = requests.Session()
        self.hrequests_session = hrequests.Session()
        self.fetch_descriptions = fetch_descriptions

    def setup_driver(self):
        driver = super().setup_driver()
        if driver:
            self.wait = WebDriverWait(driver, 10)
        return driver
    
    def navigate_to_search_page(self, job_title, location):
        """Navigate to search page using hrequests first, Selenium fallback"""
        try:
            logging.info(f"Searching Indeed for {job_title} in {location}")
            
            # Build search URL with filters
            params = {
                'q': job_title,
                'l': location,
                'fromage': '1',  # Last 24 hours
                'sort': 'date'   # Sort by date
            }
            
            search_url = f"{self.base_url}/jobs?" + urllib.parse.urlencode(params)
            logging.info(f"Navigating to search URL with filters: {search_url}")
            
            # Try hrequests first (primary method)
            try:
                response = self.hrequests_session.get(
                    search_url,
                    timeout=15,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                    }
                )
                
                if response.status_code == 200 and ('[data-jk]' in response.text or 'job_seen_beacon' in response.text):
                    self.last_page_source = response.text
                    logging.info("Job listings found via hrequests")
                    return True
                    
            except Exception as e:
                logging.warning(f"hrequests failed: {e}, falling back to Selenium")
            
            # Selenium fallback
            self.driver.get(search_url)
            time.sleep(random.uniform(5, 10))  # Increased wait time to let challenge fully load
            
            # Check for challenges
            if self._check_for_challenge():
                return False
                
            # Wait for job results
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-jk]"))
            )
            logging.info("Search with filters successful!")
            return True
            
        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False
    
    def _check_for_challenge(self):
        """Enhanced challenge detection with Cloudflare bypass capability"""
        try:
            # Wait a bit more for page to fully load
            time.sleep(random.uniform(2, 4))
            
            # Check for basic Indeed challenge indicators
            challenge_indicators = [
                "//h1[contains(text(), 'Additional Verification Required')]",
                "//h1[contains(text(), 'Security Check')]"
            ]
            
            for indicator in challenge_indicators:
                if self.driver.find_elements(By.XPATH, indicator):
                    logging.error("Indeed challenge page detected")
                    return True
            
            # Check for Cloudflare challenges using specialized detection
            if is_cloudflare_challenge(self.driver):
                logging.error("Cloudflare challenge detected")
                
                # Wait a bit more for challenge to fully load before attempting bypass
                time.sleep(random.uniform(3, 6))
                
                # Use centralized bypass function
                current_url = self.driver.current_url
                bypassed_driver = bypass_cloudflare_challenge(
                    current_url, 
                    headless=False,  # Keep visible for interview demo
                    max_retries=2
                )
                
                if bypassed_driver:
                    # Replace current driver with bypassed one
                    old_driver = self.driver
                    self.driver = bypassed_driver
                    self.wait = WebDriverWait(self.driver, 10)
                    
                    # Clean up old driver
                    try:
                        old_driver.quit()
                    except:
                        pass
                    
                    logging.info("Successfully bypassed Cloudflare challenge!")
                    return False  # No challenge detected after bypass
                else:
                    logging.error("Failed to bypass Cloudflare challenge")
                    return True  # Challenge still present
            
            return False
        except:
            return False

    def get_page_source_for_parsing(self):
        """Get page source from hrequests or Selenium"""
        if hasattr(self, 'last_page_source') and self.last_page_source:
            return self.last_page_source
        return self.driver.page_source if self.driver else ""

    def extract_job_cards(self, html_content):
        """Extract job cards using proven working selectors"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Primary selector
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        if not job_cards:
            # Fallback selectors
            job_cards = soup.find_all('div', {'data-jk': True}) or soup.find_all('div', class_='slider_container')

        logging.info(f"Found {len(job_cards)} job cards")
        return job_cards

    def extract_job_details(self, job_card):
        """Extract job details with essential selectors only"""
        try:
            # Debug first card only
            if not hasattr(self, '_debug_done'):
                self._debug_job_card(job_card)
                self._debug_done = True

            # Extract title and URL
            title, job_url = "N/A", None
            
            title_selectors = [
                'h2 a span[title]',
                'a[data-jk] span[title]',
                '[data-testid="job-title"]'
            ]
            
            for selector in title_selectors:
                title_elem = job_card.select_one(selector)
                if title_elem:
                    title = title_elem.get('title') or title_elem.get_text(strip=True)
                    link_elem = title_elem.find_parent('a')
                    if link_elem and link_elem.get('href'):
                        job_url = f"{self.base_url}{link_elem['href']}"
                    break

            # Extract company
            company_selectors = [
                'span[data-testid="company-name"]',
                'a[data-testid="company-name"]',
                '.companyName',
                'span.companyName'
            ]
            
            company = "N/A"
            for selector in company_selectors:
                company_elem = job_card.select_one(selector)
                if company_elem:
                    company = company_elem.get_text(strip=True)
                    if company and company != "N/A":
                        break

            # Extract location
            location_selectors = [
                'div[data-testid="job-location"]',
                'div[data-testid="text-location"]',
                '.companyLocation'
            ]
            
            location = "N/A"
            for selector in location_selectors:
                location_elem = job_card.select_one(selector)
                if location_elem:
                    location_text = location_elem.get_text(strip=True)
                    # Clean location text
                    if company != "N/A" and location_text.startswith(company):
                        location = location_text[len(company):].strip()
                    else:
                        location = location_text
                    location = self._clean_location(location)
                    break
            
            # Fallback location extraction
            if location == "N/A":
                job_text = job_card.get_text(separator=' | ', strip=True)
                location = self._extract_location_from_text(job_text)

            logging.info(f"Extracted - Title: {title}, Company: {company}, Location: {location}")

            return {
                'title': title,
                'company': company,
                'location': location,
                'url': job_url,
                'description': (self.fetch_job_description_hrequests(job_url) 
                              if job_url and self.fetch_descriptions 
                              else "Description fetching disabled"),
                'source': 'Indeed'
            }
        except Exception as e:
            logging.error(f"Error extracting job details: {e}")
            return None

    def _debug_job_card(self, job_card):
        """Debug method for first job card only"""
        try:
            with open("debug_job_card.html", "w", encoding="utf-8") as f:
                f.write(str(job_card.prettify()))
            logging.info("Saved job card HTML to debug_job_card.html")
            
            all_text = job_card.get_text(separator='|', strip=True)
            logging.info(f"Job card text content: {all_text[:500]}...")
        except Exception as e:
            logging.error(f"Debug error: {e}")

    def _clean_location(self, location_text):
        """Clean and normalize location text"""
        if not location_text:
            return "N/A"
        
        location = location_text.strip()
        
        # Handle "Remote in City, State" pattern  
        remote_in_pattern = r'Remote in (.+?)(?:\s+\d{5}(?:-\d{4})?)?$'
        match = re.search(remote_in_pattern, location, re.IGNORECASE)
        if match:
            city_state = match.group(1).strip()
            return f"Remote in {city_state}"
        
        # Handle simple "Remote"
        if location.lower() == 'remote':
            return "Remote"
        
        # Clean up formatting
        location = re.sub(r'\s+', ' ', location)
        location = re.sub(r',\s*,', ',', location)
        
        return location
    
    def _extract_location_from_text(self, job_text):
        """Extract location from job text using patterns"""
        if not job_text:
            return "N/A"
        
        # Check for Remote patterns
        if 'Remote in' in job_text:
            remote_pattern = r'Remote in ([^|]+?)(?:\s+\d{5}(?:-\d{4})?)?(?:\s*\||\s*$)'
            match = re.search(remote_pattern, job_text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                return f"Remote in {location}"
        
        if 'Remote' in job_text or 'remote' in job_text.lower():
            return "Remote"
        
        # Try city, state patterns
        city_state_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\s*\d{5}\b',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b',
            r'\b([A-Z][a-z]+),\s*([A-Z][a-z]+)\b'
        ]
        
        for pattern in city_state_patterns:
            matches = re.findall(pattern, job_text)
            if matches:
                city, state = matches[0]
                return f"{city}, {state}"
        
        return "N/A"

    def _clean_job_description(self, description):
        """Clean job description by removing structural headers"""
        if not description or description in ["Description not available", "Description fetching disabled"]:
            return description
        
        # Patterns to remove
        patterns_to_remove = [
            r'^Job Description:?\s*',
            r'^Overview:?\s*',
            r'^Position Objective:?\s*', 
            r'^Job Summary:?\s*',
            r'^About the Role:?\s*',
            r'^Description:?\s*',
            r'^The Role:?\s*'
        ]
        
        cleaned_description = description
        for pattern in patterns_to_remove:
            cleaned_description = re.sub(pattern, '', cleaned_description, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up whitespace
        cleaned_description = re.sub(r'\n\s*\n', '\n\n', cleaned_description)
        cleaned_description = re.sub(r'^\s+|\s+$', '', cleaned_description)
        
        return cleaned_description.strip()
        
    def fetch_job_description_hrequests(self, job_url):
        """Fetch job description using hrequests"""
        if not job_url or not self.fetch_descriptions:
            return "Description fetching disabled"
        
        try:
            resp = self.hrequests_session.get(
                job_url,
                timeout=15,
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
            
            # Primary selector
            desc_elem = soup.find('div', id='jobDescriptionText')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
                logging.info(f"Found description using primary selector: {len(description)} chars")
            else:
                # Fallback selectors
                fallback_selectors = [
                    {'class_': 'jobsearch-JobComponent-description'},
                    {'class_': 'jobsearch-jobDescriptionText'}, 
                    {'class_': re.compile(r'jobDescription')},
                ]
                
                description = None
                for selector in fallback_selectors:
                    desc_elem = soup.find('div', selector)
                    if desc_elem:
                        description = desc_elem.get_text(strip=True)
                        break
            
            # Validate and return
            if description and len(description) > 50:
                # Clean and limit length
                description = re.sub(r'\s+', ' ', description)
                description = self._clean_job_description(description)
                
                if len(description) > 3000:
                    description = description[:3000] + "... [truncated]"
                
                logging.info(f"Successfully fetched description: {len(description)} characters")
                return description
            else:
                return "Description not found or too short"
                
        except Exception as e:
            logging.error(f"Error fetching description: {str(e)[:100]}")
            return "Description not available"
    
    def scrape_jobs(self, job_title, location, max_jobs=20):
        """Main scraping method"""
        jobs = []

        try:
            if not self.setup_driver():
                return []
            
            if not self.navigate_to_search_page(job_title, location):
                return []
            
            html_content = self.get_page_source_for_parsing()
            job_cards = self.extract_job_cards(html_content)

            if not job_cards:
                logging.warning("No job cards found")
                return []
            
            for card in job_cards:
                if len(jobs) >= max_jobs:
                    break

                job_data = self.extract_job_details(card)
                if job_data:
                    jobs.append(job_data)
                    logging.info(f"Extracted: {job_data['title']} at {job_data['company']}")
                
        except Exception as e:
            logging.error(f"Scraping error: {e}")
        finally:
            self.quit_driver()

        return jobs[:max_jobs]