"""
Cloudflare Bypass Module using undetected-chromedriver

This module provides specialized functions to bypass Cloudflare challenges
and can be integrated into existing scrapers' challenge detection methods.

Usage:
    from scraper.cloudflare_bypass import bypass_cloudflare_challenge, is_cloudflare_challenge

Installation required:
    pip install undetected-chromedriver
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import random
import logging
import os
import tempfile
from urllib.parse import urljoin, urlparse


class CloudflareBypass:
    """
    Specialized class for handling Cloudflare challenges with undetected-chromedriver.
    Designed to be a drop-in solution for existing scrapers.
    """
    
    def __init__(self, headless=False, use_persistent_profile=True):
        self.driver = None
        self.wait = None
        self.headless = headless
        self.use_persistent_profile = use_persistent_profile
        self.profile_dir = None
        
        # Setup persistent profile for better stealth
        if use_persistent_profile:
            self.profile_dir = os.path.join(tempfile.gettempdir(), "cf_bypass_profile")
            os.makedirs(self.profile_dir, exist_ok=True)
    
    def _create_undetected_driver(self):
        """Create an undetected Chrome driver optimized for Cloudflare bypass"""
        try:
            options = uc.ChromeOptions()
            
            # Essential anti-detection options
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check") 
            options.add_argument("--disable-logging")
            options.add_argument("--disable-gpu-logging")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            # Remove problematic excludeSwitches option for compatibility
            # options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Window and stealth settings
            if not self.headless:
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--start-maximized")
            
            # Persistent profile for consistency
            if self.use_persistent_profile and self.profile_dir:
                options.add_argument(f"--user-data-dir={self.profile_dir}")
            
            # Additional Cloudflare-specific options
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-translate")
            options.add_argument("--disable-features=VizDisplayCompositor")
            
            # Create undetected driver
            driver = uc.Chrome(
                options=options,
                headless=self.headless,
                use_subprocess=True,
                version_main=None,  # Auto-detect
            )
            
            # Additional stealth measures
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": driver.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
            })
            
            self.driver = driver
            self.wait = WebDriverWait(driver, 30)  # Longer timeout for challenges
            
            logging.info("Undetected Chrome driver created successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create undetected driver: {e}")
            return False
    
    def is_cloudflare_challenge(self, driver=None):
        """
        Enhanced detection of Cloudflare challenges including Turnstile.
        Can be called with external driver or use internal one.
        """
        check_driver = driver or self.driver
        if not check_driver:
            return False
            
        try:
            # Check page source for Cloudflare indicators
            page_source = check_driver.page_source.lower()
            
            # Cloudflare challenge indicators
            cf_indicators = [
                'cloudflare',
                'cf-challenge',
                'checking your browser',
                'please wait',
                'ddos protection',
                'challenge-form',
                'turnstile',
                'cf-ray',
                'just a moment',
                'security check',
                'verify you are human',
                'cf-browser-verification',
                'challenge-platform'
            ]
            
            for indicator in cf_indicators:
                if indicator in page_source:
                    logging.warning(f"Cloudflare challenge detected: {indicator}")
                    return True
            
            # Check URL patterns
            current_url = check_driver.current_url.lower()
            cf_url_patterns = [
                'challenge',
                'cdn-cgi',
                'cf-under-attack',
                'cloudflare'
            ]
            
            for pattern in cf_url_patterns:
                if pattern in current_url:
                    logging.warning(f"Cloudflare URL pattern detected: {pattern}")
                    return True
            
            # Check for specific HTML elements
            cf_elements = [
                "//div[@id='challenge-form']",
                "//div[contains(@class, 'cf-challenge')]",
                "//div[contains(@class, 'cf-wrapper')]",
                "//*[contains(text(), 'Checking your browser')]",
                "//*[contains(text(), 'DDoS protection')]",
                "//*[contains(text(), 'Cloudflare')]",
                "//iframe[contains(@src, 'challenges.cloudflare.com')]",
                "//div[@class='cf-browser-verification']"
            ]
            
            for selector in cf_elements:
                try:
                    if check_driver.find_elements(By.XPATH, selector):
                        logging.warning(f"Cloudflare element detected: {selector}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logging.error(f"Error checking for Cloudflare challenge: {e}")
            return True  # Assume challenge if we can't check
    
    def wait_for_challenge_completion(self, max_wait_time=60):
        """
        Wait for Cloudflare challenge to complete automatically.
        Returns True if challenge was passed, False if timeout.
        """
        try:
            start_time = time.time()
            logging.info("Waiting for Cloudflare challenge to complete...")
            
            while time.time() - start_time < max_wait_time:
                # Check if challenge is still present
                if not self.is_cloudflare_challenge():
                    logging.info("Cloudflare challenge completed successfully!")
                    return True
                
                # Look for success indicators
                try:
                    # Check if we can find job-related content
                    job_indicators = [
                        "[data-jk]",  # Indeed
                        "[data-jobid]",  # Glassdoor  
                        ".job",
                        ".jobsearch-SerpJobCard",
                        ".JobCard"
                    ]
                    
                    for indicator in job_indicators:
                        if self.driver.find_elements(By.CSS_SELECTOR, indicator):
                            logging.info("Job content detected - challenge passed!")
                            return True
                            
                except:
                    pass
                
                # Random delay to appear more human
                time.sleep(random.uniform(2, 4))
            
            logging.warning(f"Challenge not completed within {max_wait_time} seconds")
            return False
            
        except Exception as e:
            logging.error(f"Error waiting for challenge completion: {e}")
            return False
    
    def bypass_with_retry(self, url, max_retries=3):
        """
        Attempt to bypass Cloudflare challenge with retry logic.
        Returns True if successful, False otherwise.
        """
        for attempt in range(max_retries):
            try:
                logging.info(f"Bypass attempt {attempt + 1}/{max_retries} for {url}")
                
                # Create fresh driver for each attempt if needed
                if not self.driver or attempt > 0:
                    if self.driver:
                        self.driver.quit()
                    if not self._create_undetected_driver():
                        continue
                
                # Navigate to URL
                self.driver.get(url)
                
                # Add random delay
                time.sleep(random.uniform(3, 7))
                
                # Check if we hit a challenge
                if self.is_cloudflare_challenge():
                    logging.info("Cloudflare challenge detected, waiting for completion...")
                    
                    # Wait for challenge to complete
                    if self.wait_for_challenge_completion():
                        logging.info("Challenge bypassed successfully!")
                        return True
                    else:
                        logging.warning("Challenge completion timeout")
                        continue
                else:
                    logging.info("No challenge detected - direct access successful!")
                    return True
                
            except Exception as e:
                logging.error(f"Bypass attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    # Wait before retry
                    time.sleep(random.uniform(10, 20))
                    continue
        
        logging.error("All bypass attempts failed")
        return False
    
    def get_bypassed_driver(self):
        """Return the driver after successful bypass"""
        return self.driver
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logging.info("Cloudflare bypass driver cleaned up")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


# Standalone functions for integration with existing scrapers
def is_cloudflare_challenge(driver):
    """
    Standalone function to check if current page has Cloudflare challenge.
    Can be used as a drop-in replacement for existing challenge detection.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if Cloudflare challenge detected, False otherwise
    """
    bypass = CloudflareBypass()
    return bypass.is_cloudflare_challenge(driver)


def bypass_cloudflare_challenge(url, headless=False, max_retries=3):
    """
    Standalone function to bypass Cloudflare challenge for a URL.
    Returns a driver that has successfully bypassed the challenge.
    
    Args:
        url (str): URL to access
        headless (bool): Whether to run in headless mode
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        WebDriver: Driver instance with bypassed challenge, or None if failed
    """
    bypass = CloudflareBypass(headless=headless)
    
    if bypass.bypass_with_retry(url, max_retries):
        return bypass.get_bypassed_driver()
    else:
        bypass.cleanup()
        return None


def create_enhanced_challenge_checker(existing_check_function=None):
    """
    Factory function to create an enhanced challenge checker that combines
    existing logic with Cloudflare-specific detection.
    
    Args:
        existing_check_function: Optional existing challenge check function
        
    Returns:
        function: Enhanced challenge checker
    """
    def enhanced_check_for_challenge(driver):
        """Enhanced challenge checker with Cloudflare support"""
        
        # First run existing check if provided
        if existing_check_function:
            if existing_check_function(driver):
                return True
        
        # Then check for Cloudflare specifically
        return is_cloudflare_challenge(driver)
    
    return enhanced_check_for_challenge


# Integration helper for existing scrapers
def integrate_cloudflare_bypass(scraper_class):
    """
    Class decorator to integrate Cloudflare bypass into existing scrapers.
    
    Usage:
        @integrate_cloudflare_bypass
        class MyExistingScraper(BaseScraper):
            # existing code...
    """
    
    # Store original methods
    original_setup_driver = getattr(scraper_class, 'setup_driver', None)
    original_check_for_challenge = getattr(scraper_class, '_check_for_challenge', None)
    
    def enhanced_setup_driver(self):
        """Enhanced setup that can fall back to undetected driver"""
        if original_setup_driver:
            driver = original_setup_driver(self)
            if driver:
                return driver
        
        # Fallback to undetected driver
        logging.info("Falling back to undetected Chrome driver")
        bypass = CloudflareBypass(headless=getattr(self, 'headless', False))
        if bypass._create_undetected_driver():
            self.driver = bypass.get_bypassed_driver()
            return self.driver
        return None
    
    def enhanced_check_for_challenge(self):
        """Enhanced challenge check with Cloudflare support"""
        
        # Run original check if exists
        if original_check_for_challenge:
            if original_check_for_challenge(self):
                return True
        
        # Check for Cloudflare specifically
        return is_cloudflare_challenge(self.driver)
    
    # Replace methods
    scraper_class.setup_driver = enhanced_setup_driver
    scraper_class._check_for_challenge = enhanced_check_for_challenge
    
    return scraper_class