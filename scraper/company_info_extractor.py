"""
Company Info Extractor
    - Searches company on Google using Selenium
    - Skips social/info sites  
    - Extracts emails from contact pages
    - Uses Selenium + BeautifulSoup4 + requests
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from .base_scraper import BaseScraper

class CompanyInfoExtractor(BaseScraper):
    def __init__(self):
        """
        Company info extractor using Selenium for Google search + requests for email extraction
        Inherits from BaseScraper for standardized Selenium setup.
        """
        super().__init__()  # Initialize BaseScraper
        
        # Setup requests session for email extraction
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Excluded domains (social media, info sites)
        self.excluded_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'tiktok.com', 'wikipedia.org', 'quora.com',
            'reddit.com', 'glassdoor.com', 'indeed.com', 'ziprecruiter.com'
        ]
        
        logging.info("CompanyInfoExtractor initialized with BaseScraper")

        # Email extraction patterns
        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
        ]

    def _setup_selenium_driver(self):
        """
        Setup Selenium driver using BaseScraper for Google searches.
        Uses anti-detection measures and delays to avoid CAPTCHA.
        """
        if self.driver is None:
            logging.info("Setting up Selenium driver for Google search")
            
            # Add delay to avoid appearing connected to previous browser session
            import random
            delay = random.uniform(3, 8)
            logging.info(f"Waiting {delay:.2f} seconds before starting Google search browser...")
            time.sleep(delay)
            
            # Setup driver using BaseScraper
            self.driver = self.setup_driver()
            if self.driver:
                logging.info(f"Selenium driver ready ({self.browser_type})")
                return True
            else:
                logging.error("Failed to setup Selenium driver")
                return False
        return True

    def search_company_website(self, company_name):
        """
        Search for company website using Google and retrieve the first non-sponsored link.
        If the link belongs to a social website or information website like Quora or Wikipedia, it will be skipped.
        """
        if not company_name or company_name.lower() in ['n/a', 'unknown']:
            logging.warning(f"Invalid company name: '{company_name}'")
            return None
        
        try:
            search_query = f"{company_name.strip()} official website"
            logging.info(f"Google search query: '{search_query}'")
            
            # Try multiple Google access strategies
            result = self._search_google_selenium(search_query)
            if result:
                logging.info(f"Google search found: {result}")
            else:
                logging.warning(f"Google search failed for: {company_name}")
                logging.info("This might be due to persistent CAPTCHA or Google blocking.")
            return result
            
        except Exception as e:
            logging.error(f"Error searching for {company_name}: {e}")
            return None

    def _check_for_captcha(self):
        """
        Check if Google is showing a CAPTCHA page.
        Returns True if CAPTCHA detected, False otherwise.
        """
        try:
            # Common CAPTCHA indicators on Google
            captcha_indicators = [
                "Our systems have detected unusual traffic",
                "captcha",
                "recaptcha",
                "robot",
                "automated queries",
                "confirm you're not a robot"
            ]
            
            page_text = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            
            # Check page content for CAPTCHA indicators
            for indicator in captcha_indicators:
                if indicator in page_text or indicator in page_title:
                    logging.warning(f"CAPTCHA indicator found: '{indicator}'")
                    return True
            
            # Check for specific reCAPTCHA checkbox element (captured from real page)
            try:
                recaptcha_checkbox = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".recaptcha-checkbox-border")
                if recaptcha_checkbox:
                    logging.warning(f"Found reCAPTCHA checkbox element: {len(recaptcha_checkbox)} elements")
                    return True
            except:
                pass
                    
            # Check for other CAPTCHA form elements
            try:
                captcha_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "[id*='captcha'], [class*='captcha'], [id*='recaptcha'], [class*='recaptcha']")
                if captcha_elements:
                    logging.warning(f"Found {len(captcha_elements)} general CAPTCHA elements")
                    return True
            except:
                pass
                
            return False
            
        except Exception as e:
            logging.warning(f"Error checking for CAPTCHA: {e}")
            return False

    def _attempt_captcha_solve(self):
        """
        Attempt to automatically solve reCAPTCHA by clicking the "I'm not a robot" checkbox.
        Returns True if CAPTCHA appears to be solved, False otherwise.
        """
        try:
            logging.info("🤖 Attempting to solve reCAPTCHA automatically...")
            
            # Try multiple selectors to find the reCAPTCHA checkbox
            checkbox_selectors = [
                ".recaptcha-checkbox",  # Main checkbox container
                ".recaptcha-checkbox-border",  # The element we captured
                "[role='checkbox']",  # Accessibility role
                "iframe[title*='reCAPTCHA'] + div .recaptcha-checkbox",  # In case it's after iframe
            ]
            
            checkbox_element = None
            
            # First, check if reCAPTCHA is in an iframe
            try:
                recaptcha_iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[title*='reCAPTCHA']")
                if recaptcha_iframes:
                    logging.info(f"Found {len(recaptcha_iframes)} reCAPTCHA iframe(s)")
                    
                    # Switch to the reCAPTCHA iframe
                    self.driver.switch_to.frame(recaptcha_iframes[0])
                    logging.info("Switched to reCAPTCHA iframe")
                    
                    # Now try to find checkbox inside iframe
                    for selector in checkbox_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                checkbox_element = elements[0]
                                logging.info(f"Found reCAPTCHA checkbox in iframe with selector: {selector}")
                                break
                        except:
                            continue
                            
            except Exception as iframe_error:
                logging.warning(f"Error checking for reCAPTCHA iframe: {iframe_error}")
            
            # If not found in iframe, try in main page
            if not checkbox_element:
                # Switch back to main content if we were in iframe
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                
                # Try to find checkbox in main page
                for selector in checkbox_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            checkbox_element = elements[0]
                            logging.info(f"Found reCAPTCHA checkbox in main page with selector: {selector}")
                            break
                    except:
                        continue
            
            if not checkbox_element:
                logging.error("❌ Could not find reCAPTCHA checkbox element")
                return False
            
            # Check if checkbox is already checked
            try:
                if checkbox_element.get_attribute("aria-checked") == "true":
                    logging.info("✅ reCAPTCHA checkbox already checked!")
                    self.driver.switch_to.default_content()  # Switch back to main content
                    return True
            except:
                pass
            
            # Try to click the checkbox
            logging.info("🖱️  Clicking reCAPTCHA checkbox...")
            
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox_element)
            time.sleep(1)
            
            # Try clicking with JavaScript first (more reliable)
            try:
                self.driver.execute_script("arguments[0].click();", checkbox_element)
                logging.info("Clicked reCAPTCHA checkbox with JavaScript")
            except:
                # Fallback to regular click
                checkbox_element.click()
                logging.info("Clicked reCAPTCHA checkbox with Selenium")
            
            # Wait for verification to complete
            logging.info("⏳ Waiting for reCAPTCHA verification...")
            time.sleep(3)
            
            # Check if verification was successful
            verification_wait = WebDriverWait(self.driver, 10)
            
            try:
                # Look for signs that reCAPTCHA was solved
                # Method 1: Check if checkbox is now checked
                if checkbox_element.get_attribute("aria-checked") == "true":
                    logging.info("✅ reCAPTCHA verification successful (checkbox checked)!")
                    self.driver.switch_to.default_content()  # Switch back to main content
                    return True
                    
            except Exception as check_error:
                logging.warning(f"Error checking checkbox state: {check_error}")
            
            # Method 2: Check if we're redirected to search results
            try:
                self.driver.switch_to.default_content()  # Ensure we're in main content
                
                # Wait a bit more for potential redirect
                time.sleep(2)
                
                current_url = self.driver.current_url
                if "google.com/search" in current_url and "q=" in current_url:
                    logging.info("✅ reCAPTCHA verification successful (redirected to search results)!")
                    return True
                    
            except Exception as redirect_error:
                logging.warning(f"Error checking for redirect: {redirect_error}")
            
            # Method 3: Check if CAPTCHA elements are gone
            try:
                self.driver.switch_to.default_content()
                time.sleep(1)
                
                if not self._check_for_captcha():
                    logging.info("✅ reCAPTCHA verification successful (CAPTCHA elements gone)!")
                    return True
                    
            except Exception as gone_error:
                logging.warning(f"Error checking if CAPTCHA is gone: {gone_error}")
            
            # If we get here, verification might have failed or requires additional steps
            logging.warning("⚠️  reCAPTCHA verification unclear - may require additional challenges")
            
            # Check if there's an additional challenge (image selection, etc.)
            try:
                challenge_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".rc-imageselect, .rc-audiochallenge, .fbc-imageselect")
                if challenge_elements:
                    logging.warning("🧩 reCAPTCHA requires additional challenge (images/audio) - not automated")
                    return False
            except:
                pass
            
            self.driver.switch_to.default_content()  # Ensure we're back in main content
            return False
            
        except Exception as e:
            logging.error(f"❌ Error attempting to solve reCAPTCHA: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def _search_google_selenium(self, search_query):
        """
        Search Google first non-sponsored link.
        Uses Selenium to perform Google search.
        """
        try:
            # Setup driver using BaseScraper
            if not self._setup_selenium_driver():
                logging.error("Selenium driver not available for Google search")
                return None
            
            # Navigate to Google with error handling
            google_url = f"https://google.com/search?q={search_query.replace(' ', '+')}"
            logging.info(f"Selenium Google request to: {google_url}")
            
            try:
                self.driver.get(google_url)
                logging.info("Successfully loaded Google search page")
                
                # Check for CAPTCHA immediately after loading
                if self._check_for_captcha():
                    logging.error("CAPTCHA detected on Google search page!")
                    
                    # Attempt to automatically solve the reCAPTCHA
                    logging.info("🤖 Attempting automatic reCAPTCHA solving...")
                    
                    if self._attempt_captcha_solve():
                        logging.info("🎉 reCAPTCHA solved successfully! Continuing with search...")
                        # Continue with the search process below
                    else:
                        logging.warning("❌ Failed to solve reCAPTCHA automatically")
                        
                        # Optional: Add manual solving delay if needed
                        logging.info("🕒 Adding 10-second delay for manual intervention if needed...")
                        logging.info("💡 You can manually solve the CAPTCHA now")
                        logging.info("🌐 Page URL: " + self.driver.current_url)
                        
                        # Print page title for reference
                        try:
                            logging.info("📄 Page title: " + self.driver.title)
                        except:
                            pass
                        
                        time.sleep(10)  # Reduced delay since we attempted automatic solving
                        
                        # Check again if CAPTCHA was solved during the delay
                        if not self._check_for_captcha():
                            logging.info("✅ CAPTCHA appears to be solved! Continuing...")
                        else:
                            logging.error("🚫 CAPTCHA still present, aborting search")
                            return None
                    
            except Exception as nav_error:
                logging.error(f"Failed to navigate to Google: {nav_error}")
                return None
            
            # Wait for search results to load with multiple selectors
            try:
                wait = WebDriverWait(self.driver, 15)
                # Try multiple possible selectors for search results
                wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.g")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-ved]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
                    )
                )
                logging.info("Google search results loaded")
            except TimeoutException:
                logging.warning("Timeout waiting for Google search results")
                # Still try to parse whatever loaded
            except Exception as wait_error:
                logging.error(f"Error waiting for search results: {wait_error}")
                return None
            
            # Get page source for parsing
            try:
                page_source = self.driver.page_source
                logging.info(f"Retrieved page source ({len(page_source)} characters)")
                
                # Extract first valid result using existing logic
                return self._extract_first_valid_result(page_source)
                
            except Exception as parse_error:
                logging.error(f"Error getting page source: {parse_error}")
                return None
            
        except Exception as e:
            logging.error(f"Selenium Google search failed: {e}")
            return None

    def _extract_first_valid_result(self, html_content):
        """
        Extract the first valid (non-sponsored, non-social) result from Google HTML.
        Retrieve the first non-sponsored link, skip social/info sites.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Debug: Log some of the HTML structure we received
            search_div = soup.find('div', {'id': 'search'})
            if search_div:
                logging.info("Found Google search container")
            else:
                logging.warning("No Google search container found")
                
            # Try multiple different selectors for Google results
            selectors_to_try = [
                'div.g',  # Standard Google results
                'div[data-ved]',  # Alternative results  
                'div.tF2Cxc',  # Another common Google result class
                'div.Gx5Zad',  # Yet another layout
                'h3 a',  # Direct link selector
                'a[href*="http"]'  # Any external links
            ]
            
            results = []
            for selector in selectors_to_try:
                found = soup.select(selector)
                if found:
                    logging.info(f"Found {len(found)} results with selector: {selector}")
                    results = found
                    break
            
            if not results:
                logging.warning("No search results found with any selector")
                # Debug: Save the HTML to see what Google returned
                with open('/tmp/google_debug.html', 'w') as f:
                    f.write(html_content)
                logging.info("Saved Google HTML to /tmp/google_debug.html for debugging")
                return None

            logging.info(f"Processing {len(results)} Google results")
            
            # Extract URLs from results
            for i, result in enumerate(results[:15]):  # Check first 15 results
                url = None
                
                # Try to find the URL in different ways
                if result.name == 'a' and result.get('href'):
                    # Direct link
                    url = result['href']
                else:
                    # Look for link within the result
                    link_elem = result.find('a', href=True)
                    if link_elem:
                        url = link_elem['href']
                
                if not url:
                    continue
                    
                # Clean up Google redirect URLs
                if url.startswith('/url?q='):
                    import urllib.parse
                    parsed_url = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                    if 'q' in parsed_url:
                        url = parsed_url['q'][0]
                elif url.startswith('/search') or url.startswith('#'):
                    # Skip internal Google links
                    continue
                
                logging.info(f"Google result {i+1}: {url}")
                
                # Check if this is a valid company website (not social/info site)
                if self._is_valid_company_website(url):
                    logging.info(f"SUCCESS: Found first valid company website: {url}")
                    return url
                else:
                    logging.info(f"Skipped (social/info site): {url}")
            
            logging.warning("No valid company websites found in Google results")
            return None
            
        except Exception as e:
            logging.error(f"Error extracting Google results: {e}")
            return None

    def _is_valid_company_website(self, url):
        """
        Check if URL is valid company website.
        Skip social websites and info sites like Quora, Wikipedia.
        """
        if not url or not url.startswith('http'):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Skip excluded domains (social media, info sites)
            for excluded in self.excluded_domains:
                if excluded in domain:
                    logging.info(f"Skipped excluded domain: {excluded} in {domain}")
                    return False
                
            # Skip Google redirect URLs
            if 'google.com' in domain or '/url?q=' in url:
                logging.info(f"Skipped Google URL: {domain}")
                return False
            
            return True
            
        except Exception:
            return False
    def extract_company_email(self, website_url):
        """
        Extract email from company website.
        Navigate to contact section and scrape email address.
        """
        if not website_url:
            logging.warning("No website URL provided for email extraction")
            return None
        
        try:
            logging.info(f"Starting email extraction from: {website_url}")
            
            # Pages to check for contact information
            pages_to_check = [
                website_url,
                urljoin(website_url, '/contact'),
                urljoin(website_url, '/contact-us'),
                urljoin(website_url, '/about'),
                urljoin(website_url, '/careers'),
            ]
            
            logging.info(f"Will check {len(pages_to_check)} pages for email")

            for i, page_url in enumerate(pages_to_check, 1):
                logging.info(f"Checking page {i}/{len(pages_to_check)}: {page_url}")
                email = self._extract_email_from_page(page_url)
                if email:
                    logging.info(f"SUCCESS: Email found on page {i}: {email}")
                    return email
                else:
                    logging.info(f"No email found on page {i}")
                
            logging.warning(f"No email found on any page for {website_url}")
            return None
        
        except Exception as e:
            logging.error(f"Error extracting email from {website_url}: {e}")
            logging.error(f"Exception type: {type(e).__name__}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None
        
    def _extract_email_from_page(self, page_url):
        """
        Extract email from a specific page using requests + BeautifulSoup4.
        """
        try:
            logging.info(f"Requesting page: {page_url}")
            response = self.session.get(page_url, timeout=10)
            logging.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logging.warning(f"Page request failed: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()
            
            logging.info(f"Page content length: {len(page_text)} characters")

            # Search for email patterns
            emails_found = []
            for pattern in self.email_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    logging.info(f"Found {len(matches)} email matches with pattern: {pattern}")
                    for email in matches:
                        if self._is_company_email(email):
                            logging.info(f"SUCCESS: Valid company email: {email}")
                            return email.lower()
                        else:
                            logging.info(f"Skipped email (not company): {email}")
                            emails_found.append(email)
            
            if emails_found:
                logging.info(f"Found {len(emails_found)} emails but none were company emails: {emails_found}")
            else:
                logging.info("No email patterns found on page")
            
            return None
        
        except Exception as e:
            logging.warning(f"Could not extract email from {page_url}: {e}")
            return None
        
    def _is_company_email(self, email):
        """
        Filter out non-company emails (personal emails, noreply, etc.)
        """
        email = email.lower()
        
        # Skip common non-company patterns
        excluded_patterns = [
            'noreply@', 'no-reply@', 'donotreply@',
            'newsletter@', 'marketing@',
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'
        ]
        
        for pattern in excluded_patterns:
            if pattern in email:
                return False

        # Preferred company contact emails
        preferred_patterns = [
            'info@', 'contact@', 'hello@', 'careers@', 'jobs@', 'hr@'
        ]

        for pattern in preferred_patterns:
            if pattern in email:
                return True
            
        return '@' in email and '.' in email
        
    def enhance_job_with_company_info(self, job_data):
        """
        Enhance job data with company website and email.
        """
        company_name = job_data.get('company')
        if not company_name:
            logging.warning("No company name provided, skipping enhancement")
            return job_data

        logging.info(f"ENHANCING: {company_name}")
        
        # Delay to be respectful
        time.sleep(1)

        # Search for company website
        logging.info(f"Searching for website: {company_name}")
        website = self.search_company_website(company_name)
        job_data['company_website'] = website
        
        if website:
            logging.info(f"Found website: {website}")
            # Extract email from company website
            time.sleep(1)
            logging.info(f"Searching for email on: {website}")
            email = self.extract_company_email(website)
            job_data['company_email'] = email
            if email:
                logging.info(f"Found email: {email}")
            else:
                logging.warning(f"No email found on {website}")
        else:
            logging.warning(f"No website found for {company_name}")
            job_data['company_email'] = None

        logging.info(f"Enhancement complete for {company_name}")
        return job_data
    
    def cleanup(self):
        """
        Clean up resources using BaseScraper's cleanup method.
        """
        try:
            # Use BaseScraper's driver cleanup
            self.quit_driver()
        except Exception as e:
            logging.warning(f"Error during driver cleanup: {e}")
        
        # Close requests session
        if hasattr(self, 'session') and self.session:
            self.session.close()
            logging.info("Closed requests session")