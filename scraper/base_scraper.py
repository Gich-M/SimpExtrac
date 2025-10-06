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
    def __init__(self):
        self.driver = None
        self.browser_type = None

    def _get_chrome_options(self):
        """Get Chrome options optimized for Windows with anti-detection"""
        chrome_options = Options()
        
        # Basic options - make it look less like automation
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu-logging")
        
        # Advanced anti-detection measures
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # More realistic user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.207 Safari/537.36")
        
        # Additional stealth options
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--ignore-certificate-errors")
        
        return chrome_options

    def _get_firefox_options(self):
        """Get Firefox options as fallback"""
        firefox_options = FirefoxOptions()
        firefox_options.add_argument("--headless")
        firefox_options.add_argument("--width=1280")
        firefox_options.add_argument("--height=720")
        return firefox_options

    def _try_chrome(self):
        """Try to setup Chrome driver"""
        try:
            logging.info("Attempting Chrome setup...")
            chrome_options = self._get_chrome_options()
            service = ChromiumService(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(20)
            driver.implicitly_wait(5)
            
            # Test the driver with a simple page
            driver.get("about:blank")
            logging.info("Chrome driver successful")
            return driver
            
        except Exception as e:
            logging.error(f"Chrome failed: {e}")
            return None

    def _try_firefox(self):
        """Try to setup Firefox driver as fallback"""
        try:
            logging.info("Attempting Firefox setup...")
            firefox_options = self._get_firefox_options()
            service = FirefoxService(GeckoDriverManager().install())
            
            driver = webdriver.Firefox(service=service, options=firefox_options)
            driver.set_page_load_timeout(20)
            driver.implicitly_wait(5)
            
            # Test the driver
            driver.get("about:blank")
            logging.info("Firefox driver successful")
            return driver
            
        except Exception as e:
            logging.error(f"Firefox failed: {e}")
            return None

    def setup_driver(self):
        """Setup driver with Chrome first, Firefox fallback"""
        try:
            logging.info("Starting driver setup...")
            
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
            logging.error(f"Failed to setup any driver: {e}")
            return None
        
    def quit_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                logging.info(f"Closed {self.browser_type} driver")
            except Exception as e:
                logging.error(f"Error closing driver: {e}")