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

class GlassdoorScraper(BaseScraper):
    def __init__(self, fetch_descriptions=True):
        super().__init__()
        self.base_url = "https://www.glassdoor.com/Job/index.htm"
        self.wait = None
        self.session = requests.Session()
        self.hrequests_session = hrequests.Session()
        self.fetch_descriptions = fetch_descriptions

    def setup_driver(self):
        driver = super().setup_driver()
        if driver:
            self.wait = WebDriverWait(driver, 10)
        return driver

    def navigate_search_page(self, job_title, location):
        """Navigate to search results using hrequests first, Selenium fallback"""
        try:
            logging.info(f"Searching Glassdoor for {job_title} in {location}")
            
            # Build direct search URL
            encoded_title = urllib.parse.quote(job_title)
            encoded_location = urllib.parse.quote(location)
            search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_title}&locKeyword={encoded_location}"
            
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
                
                if response.status_code == 200 and ('data-jobid' in response.text or '/job/' in response.text):
                    self.last_page_source = response.text
                    logging.info("Job listings found via hrequests")
                    return True
                    
            except Exception as e:
                logging.warning(f"hrequests failed: {e}, falling back to Selenium")
            
            # Selenium fallback
            self.driver.get(search_url)
            time.sleep(random.uniform(5, 10))
            
            # Check for Cloudflare challenges first
            if is_cloudflare_challenge(self.driver):
                logging.warning("Cloudflare challenge detected, attempting bypass...")
                
                # Use centralized bypass function
                bypassed_driver = bypass_cloudflare_challenge(
                    search_url, 
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
                    
                    logging.info("Cloudflare bypass successful")
                else:
                    logging.error("Cloudflare bypass failed")
                    return False
            
            # Check for job listings
            if self.driver.find_elements(By.CSS_SELECTOR, "[data-jobid]"):
                logging.info("Job listings found via Selenium")
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Navigation failed: {e}")
            return False

    def get_page_source_for_parsing(self):
        """Get page source from hrequests or Selenium"""
        if hasattr(self, 'last_page_source') and self.last_page_source:
            return self.last_page_source
        return self.driver.page_source if self.driver else ""
    
    def extract_job_cards(self, html_content):
        """Extract job cards using proven working selector"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.select('li[data-jobid]')
        
        if not job_cards:
            # Fallback to any job links
            job_cards = soup.find_all('a', href=lambda x: x and '/job/' in x)
        
        logging.info(f"Found {len(job_cards)} job cards")
        return job_cards
    
    def extract_job_details(self, job_card):
        """Extract job details with debugging for hrequests HTML structure"""
        try:
            # Debug first card to understand hrequests HTML structure
            if not hasattr(self, '_debug_done'):
                self._debug_glassdoor_card(job_card)
                self._debug_done = True

            # Extract title and URL
            if job_card.name == 'a' and job_card.get('href'):
                title = job_card.get_text(strip=True)
                job_url = job_card['href']
            else:
                # Look for title link within card - enhanced selectors
                title_selectors = [
                    'a[data-test="job-title"]',
                    'a[href*="/job/"]',
                    '.JobCard_jobTitle a',
                    'h3 a',
                    'h2 a'
                ]
                
                title_elem = None
                for selector in title_selectors:
                    title_elem = job_card.select_one(selector)
                    if title_elem:
                        break
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    job_url = title_elem.get('href', '')
                else:
                    return None
            
            # Make URL absolute
            if job_url and not job_url.startswith('http'):
                job_url = 'https://www.glassdoor.com' + job_url
            
            # Extract company - enhanced selectors for hrequests response
            company_selectors = [
                'span[data-test="employer-name"]',
                '.company',
                '.employerName', 
                'a[data-test="employer-name"]',
                '.JobCard_employerName',
                'span[class*="EmployerProfile"]',
                'span[class*="employer"]',
                '[data-test="employer"]',
                'div[data-test="employer-name"]'
            ]
            
            company = "N/A"
            for selector in company_selectors:
                company_elem = job_card.select_one(selector)
                if company_elem:
                    company_text = company_elem.get_text(strip=True)
                    if company_text and company_text != "N/A" and len(company_text) > 1:
                        company = company_text
                        break

            # If still no company, try broader search within the job card
            if company == "N/A":
                # Look for any element that might contain company name
                # Often in hrequests response, company might be in different structure
                all_spans = job_card.find_all('span')
                for span in all_spans:
                    text = span.get_text(strip=True)
                    # Skip obvious non-company text
                    if (text and len(text) > 2 and len(text) < 100 and 
                        not any(skip_word in text.lower() for skip_word in 
                               ['remote', 'full-time', 'part-time', 'salary', 'hour', 'day', 'ago', 'new'])):
                        # This might be company name - take first reasonable candidate
                        company = text
                        break

            # Extract location - enhanced selectors
            location_selectors = [
                '[data-test="job-location"]',
                '.location',
                '.JobCard_location',
                'div[class*="location"]',
                'span[class*="location"]',
                'div[data-test="job-location"]'
            ]
            
            location = "N/A"
            for selector in location_selectors:
                location_elem = job_card.select_one(selector)
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    if location and location != "N/A":
                        break

            # Extract salary if available
            salary_selectors = [
                '[data-test="salary"]',
                '.salary',
                '.JobCard_salary',
                'span[class*="salary"]',
                '[class*="pay"]'
            ]
            
            salary = "N/A"
            for selector in salary_selectors:
                salary_elem = job_card.select_one(selector)
                if salary_elem:
                    salary = salary_elem.get_text(strip=True)
                    if salary and salary != "N/A":
                        break

            return {
                'title': title,
                'company': company,
                'location': location,
                'salary': salary,
                'url': job_url,
                'description': (self.fetch_job_description(job_url) 
                              if job_url and self.fetch_descriptions 
                              else "Description fetching disabled"),
                'source': 'Glassdoor'
            }
        except Exception as e:
            logging.error(f"Error extracting job details: {e}")
            return None
        
    def _debug_glassdoor_card(self, job_card):
        """Debug method to understand Glassdoor's hrequests HTML structure"""
        try:
            with open("debug_glassdoor_card.html", "w", encoding="utf-8") as f:
                f.write(str(job_card.prettify()))
            logging.info("Saved Glassdoor job card HTML to debug_glassdoor_card.html")
            
            # Print structure for analysis
            all_text = job_card.get_text(separator=' | ', strip=True)
            logging.info(f"Glassdoor card text: {all_text[:300]}...")
            
            # Print all span elements to find company selector
            spans = job_card.find_all('span')
            logging.info(f"Found {len(spans)} span elements in job card")
            for i, span in enumerate(spans[:10]):  # First 10 spans
                text = span.get_text(strip=True)
                if text:
                    logging.info(f"Span {i}: '{text}' - classes: {span.get('class', 'none')}")
                    
        except Exception as e:
            logging.error(f"Debug error: {e}")
        
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
        """Fetch job description using hrequests with improved timeout handling"""
        try:
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
                
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout fetching description from {job_url}")
            return "Description not available (timeout)"
        except Exception as e:
            logging.error(f"Error fetching description: {str(e)[:100]}")
            return "Description not available"
        
    def fetch_job_description_selenium(self, job_url):
        """Selenium fallback for job description fetching"""
        if not job_url:
            return "Description not available"

        try:
            current_window = self.driver.current_window_handle
            self.driver.execute_script(f"window.open('{job_url}', '_blank');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            time.sleep(random.uniform(2, 4))
            
            # Use proven working selector
            try:
                desc_elem = self.driver.find_element(By.CSS_SELECTOR, 'div[class*="JobDetails_jobDescription"]')
                description = desc_elem.text.strip()
                description = self._clean_job_description(description)
            except:
                description = "Description not available"
            
            self.driver.close()
            self.driver.switch_to.window(current_window)
            return description
            
        except Exception as e:
            logging.error(f"Selenium description fetch failed: {e}")
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(current_window)
            except:
                pass
            return "Description not available"
    
    def fetch_job_description(self, job_url):
        """Main job description fetching method"""
        if not job_url or not self.fetch_descriptions:
            return "Description fetching disabled"
        
        # Try hrequests first
        description = self.fetch_job_description_hrequests(job_url)
        
        # Fallback to Selenium if needed
        if description == "Description not available":
            description = self.fetch_job_description_selenium(job_url)
        
        return description
    
    def scrape_jobs(self, job_title, location, max_jobs=20):
        """Main scraping method"""
        jobs = []

        try:
            if not self.setup_driver():
                return []
            
            if not self.navigate_search_page(job_title, location):
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