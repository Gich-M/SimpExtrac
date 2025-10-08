"""
Base Scraper
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import logging


class BaseScraper:
    """
    Base scraper for web scraping tasks.
    """
    def __init__(self):
        self.driver = None
        self.browser_type = None

    def _get_chrome_options(self):
        """Chrome options"""
        chrome_options = Options()
        
        # chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        return chrome_options

    def _get_firefox_options(self):
        """Firefox options as fallback"""
        firefox_options = FirefoxOptions()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--width=1920")
        firefox_options.add_argument("--height=1080")
        return firefox_options

    def _try_chrome(self):
        """Try to setup Chrome driver"""
        try:
            logging.info("Setting up Chrome driver...")
            chrome_options = self._get_chrome_options()
            service = ChromiumService(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(20)
            driver.implicitly_wait(5)
            
            # Test the driver
            driver.get("about:blank")
            logging.info("Chrome driver ready")
            return driver
            
        except Exception as e:
            logging.error(f"Chrome setup failed: {e}")
            return None

    def _try_firefox(self):
        """Try to setup Firefox driver as fallback"""
        try:
            logging.info("Setting up Firefox driver...")
            firefox_options = self._get_firefox_options()
            service = FirefoxService(GeckoDriverManager().install())
            
            driver = webdriver.Firefox(service=service, options=firefox_options)
            driver.set_page_load_timeout(20)
            driver.implicitly_wait(5)
            
            # Test the driver
            driver.get("about:blank")
            logging.info("Firefox driver ready")
            return driver
            
        except Exception as e:
            logging.error(f"Firefox setup failed: {e}")
            return None

    def setup_driver(self):
        """
        Setup WebDriver with Chrome first, Firefox fallback.
        """
        try:
            logging.info("Starting browser setup...")
            
            # Try Chrome first
            self.driver = self._try_chrome()
            if self.driver:
                self.browser_type = "chrome"
                return self.driver
            
            # Fallback to Firefox
            logging.warning("Chrome failed, trying Firefox...")
            self.driver = self._try_firefox()
            if self.driver:
                self.browser_type = "firefox"
                return self.driver
            
            logging.error("Both Chrome and Firefox failed")
            return None
            
        except Exception as e:
            logging.error(f"Driver setup failed: {e}")
            return None
        
    def quit_driver(self):
        """Clean up WebDriver resources"""
        if self.driver:
            try:
                self.driver.quit()
                logging.info(f"Closed {self.browser_type} driver")
            except Exception as e:
                logging.error(f"Error closing driver: {e}")