import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CompanyInfoExtractor:
    def __init__(self, use_selenium=False):
        self.use_selenium = use_selenium  # Disabled by default - DuckDuckGo + Domain patterns only
        self.driver = None
        self.session = requests.Session()

        # More realistic browser headers to avoid detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        self.excluded_domains = [
            'linkedin.com', 'facebook.com', 'x.com', 'instagram.com',
            'wikipedia.org', 'glassdoor.com', 'indeed.com', 'crunchbase.com',
            'youtube.com', 'github.com', 'stackoverflow.com'
        ]

        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
        ]

        # Company name normalization patterns
        self.company_suffixes = [
            'inc', 'inc.', 'corp', 'corp.', 'llc', 'ltd', 'limited', 
            'company', 'co.', 'co', 'corporation', 'incorporated'
        ]

    def _normalize_company_name(self, company_name):
        """
        Normalize company name for domain pattern matching.
        
        Args:
            company_name (str): Raw company name
            
        Returns:
            str: Normalized company name suitable for domain construction
        """
        if not company_name:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = company_name.lower().strip()
        
        # Remove common company suffixes
        words = normalized.split()
        filtered_words = []
        
        for word in words:
            # Remove punctuation and check if it's a suffix
            clean_word = word.rstrip('.,')
            if clean_word not in self.company_suffixes:
                filtered_words.append(clean_word)
        
        # Join words and remove spaces, special characters
        result = ''.join(filtered_words)
        # Keep only alphanumeric characters
        result = ''.join(c for c in result if c.isalnum())
        
        return result

    def _search_duckduckgo(self, company_name):
        """
        Search for company website using DuckDuckGo.
        More automation-friendly than Google.
        
        Args:
            company_name (str): Company name to search for
            
        Returns:
            str: Company website URL or None if not found
        """
        try:
            import time
            import random
            
            # Add small random delay to be respectful
            time.sleep(random.uniform(1, 2))
            
            search_query = f"{company_name.strip()} official website"
            duckduckgo_url = f"https://duckduckgo.com/html/?q={search_query}"
            
            # Use different headers for DuckDuckGo
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            response = self.session.get(duckduckgo_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logging.debug(f"DuckDuckGo search failed with status: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # DuckDuckGo uses different selectors than Google
            # Look for result links in DuckDuckGo's HTML structure
            results = soup.find_all('a', class_='result__a')
            
            for result in results[:5]:  # Check first 5 results
                href = result.get('href')
                if href and self._is_valid_company_website(href):
                    return href
            
            # Alternative selector for DuckDuckGo results
            results = soup.find_all('a', href=True)
            for result in results:
                href = result.get('href')
                if href and href.startswith('http') and self._is_valid_company_website(href):
                    # Check if this looks like a main result (not footer, ads, etc.)
                    parent_text = result.get_text(strip=True)
                    if len(parent_text) > 10:  # Avoid short navigation links
                        return href
            
            return None
            
        except Exception as e:
            logging.debug(f"DuckDuckGo search failed for {company_name}: {e}")
            return None

    def _search_domain_patterns(self, company_name):
        """
        Try to find company website using common domain patterns.
        Fast fallback method that doesn't require external API calls.
        
        Args:
            company_name (str): Company name to search for
            
        Returns:
            str: Company website URL or None if not found
        """
        try:
            base_name = self._normalize_company_name(company_name)
            
            if not base_name or len(base_name) < 2:
                return None
            
            # Common domain patterns to try
            domain_patterns = [
                f"https://www.{base_name}.com",
                f"https://{base_name}.com",
                f"https://www.{base_name}.org",
                f"https://{base_name}.org",
                f"https://www.{base_name}.net",
                f"https://{base_name}.net"
            ]
            
            for domain in domain_patterns:
                if self._test_domain_exists(domain):
                    return domain
            
            return None
            
        except Exception as e:
            logging.debug(f"Domain pattern search failed for {company_name}: {e}")
            return None

    def _test_domain_exists(self, domain):
        """
        Test if a domain exists and is accessible.
        
        Args:
            domain (str): Domain URL to test
            
        Returns:
            bool: True if domain is accessible, False otherwise
        """
        try:
            response = self.session.head(domain, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False

    def _search_with_requests_careful(self, search_query):
        """
        Careful Google search with rate limiting protection.
        
        Args:
            search_query (str): Search query string
            
        Returns:
            str: Company website URL or None if not found
        """
        try:
            import time
            import random
            
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(3, 6))
            
            google_url = f"https://google.com/search?q={search_query}"
            response = self.session.get(google_url, timeout=10)
            
            # Check if we got blocked
            if response.status_code == 429:
                logging.warning("Google rate limited - skipping search")
                return None
            
            if response.status_code != 200:
                logging.warning(f"Google search returned status {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = soup.find_all('div', class_='g')

            for result in results[:5]:
                link_elem = result.find('a', href=True)
                if link_elem:
                    url = link_elem['href']
                    if self._is_valid_company_website(url):
                        return url
            
            return None
            
        except Exception as e:
            logging.debug(f"Careful Google search failed: {e}")
            return None

    def search_company_website(self, company_name):
        """
        Search for company website using DuckDuckGo + Domain Patterns only.
        Optimized for processing all jobs without rate limiting issues.
        
        Strategy:
        1. DuckDuckGo search (primary - reliable for automation)
        2. Domain pattern matching (fast fallback - works great for major companies)
        
        Args:
            company_name (str): Name of the company to search for
            
        Returns:
            str: Company website URL or None if not found
        """
        if not company_name or company_name.lower() in ['n/a', 'unknown']:
            return None
        
        try:
            # Strategy 1: DuckDuckGo search (primary)
            logging.debug(f"Trying DuckDuckGo search for: {company_name}")
            result = self._search_duckduckgo(company_name)
            if result:
                logging.info(f"Found company website via DuckDuckGo: {result}")
                return result
            
            # Strategy 2: Domain pattern matching (fast fallback)
            logging.debug(f"Trying domain pattern matching for: {company_name}")
            result = self._search_domain_patterns(company_name)
            if result:
                logging.info(f"Found company website via domain pattern: {result}")
                return result
            
            logging.info(f"No website found for company: {company_name}")
            return None
            
        except Exception as e:
            logging.error(f"Error searching for {company_name}: {e}")
            return None           

    def _search_with_selenium(self, search_query):
        try:
            if not self.driver:
                self.setup_selenium_driver()

            google_url = f"https://google.com/search?q={search_query}"
            self.driver.get(google_url)

            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
            )

            results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")

            for result in results[:5]:
                try:
                    link_elem = result.find_element(By.CSS_SELECTOR, "a[href]")
                    url = link_elem.get_attribute("href")

                    if self._is_valid_company_website(url):
                        logging.info(f"Found company website: {url}")
                        return url
                    
                except Exception as e:
                    continue
            
            return None
        
        except Exception as e:
            logging.error(f"Selenium google search failed: {e}")
            return None
        
    def _search_with_requests(self, search_query):
        """
        Legacy method - redirects to careful search for backward compatibility.
        
        Args:
            search_query (str): Search query string
            
        Returns:
            str: Company website URL or None if not found
        """
        return self._search_with_requests_careful(search_query)
        
    def _is_valid_company_website(self, url):
        if not url or not url.startswith('https'):
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            for excluded in self.excluded_domains:
                if excluded in domain:
                    return False
                
            if 'google.com' in domain or '/url?q=' in url:
                return False
            
            if domain.endswith('.com'):
                return True
            
            return True
        except Exception:
            return False
        
    def extract_company_email(self, website_url):
        if not website_url:
            return None
        
        try:
            pages_to_check = [
                website_url,
                urljoin(website_url, '/contact'),
                urljoin(website_url, '/contact-us'),
                urljoin(website_url, '/about'),
                urljoin(website_url, '/careers'),
                urljoin(website_url, '/jobs'),
            ]

            for page_url in pages_to_check:
                email = self._extract_email_from_page(page_url)
                if email:
                    return email
                
            return None
        
        except Exception as e:
            logging.error(f"Error extracting email from {website_url}: {e}")
            return None
        
    def _extract_email_from_page(self, page_url):
        try:
            response = self.session.get(page_url, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            for pattern in self.email_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    for email in matches:
                        if self._is_company_email(email):
                            return email.lower()
            
            return None
        
        except Exception as e:
            logging.debug(f"Could not extract email from {page_url}: {e}")
            return None
        
    def _is_company_email(self, email):
        """
        Filter out non-company emails
        """
        email = email.lower()
        
        excluded_patterns = [
            'noreply@', 'no-reply@', 'donotreply@',
            'newsletter@', 'marketing@', 'sales@',
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com'
        ]
        
        for pattern in excluded_patterns:
            if pattern in email:
                return False
        
        preferred_patterns = [
            'info@', 'contact@', 'hello@', 'careers@', 'jobs@', 'hr@'
        ]

        for pattern in preferred_patterns:
            if pattern in email:
                return True
            
        return '@' in email and '.' in email
        
    def enhance_job_with_company_info(self, job_data):
        company_name = job_data.get('company')
        if not company_name:
            return job_data
        
        # Reduced delay for faster processing of all jobs
        time.sleep(1)

        website = self.search_company_website(company_name)
        job_data['company_website'] = website

        if website:
            time.sleep(1)  # Reduced delay
            email = self.extract_company_email(website)
            job_data['company_email'] = email
        else:
            job_data['company_email'] = None

        return job_data
    
    def cleanup(self):
        """Cleanup method - simplified since we don't use Selenium"""
        pass