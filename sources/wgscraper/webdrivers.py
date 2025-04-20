import logging
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.safari.options import Options as SafariOptions

from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager

class InitWebDriver:
    """
    A dedicated class for managing WebDriver initialization with webdriver-manager fallback.
    """
    def __init__(self, url, browser="chrome", headless=True, logger=None):
        self.logger = logger or logging.getLogger
        self.browser = browser.lower()
        self.url = url
        self.headless = headless
    
    def __call__(self):
        try:
            if self.browser == "chrome":
                chrome_options = ChromeOptions()

                if self.headless:
                    self.logger.info("Adding --headless=new argument to ChromeOptions.")
                    chrome_options.add_argument("--headless=new")
                    self.logger.info("Adding comprehensive stabilization arguments to ChromeOptions.")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-extensions")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--disable-browser-side-navigation")
                    chrome_options.add_argument("--disable-default-apps")
                    chrome_options.add_argument("--disable-translate")
                    chrome_options.add_argument("--disable-background-networking")
                    chrome_options.add_argument("--disable-sync")
                    chrome_options.add_argument("--disable-client-side-phishing-detection")
                    chrome_options.add_argument("--disable-features=site-per-process")
                    chrome_options.add_argument("--metrics-recording-only")
                    chrome_options.add_argument("--disable-hang-monitor")
                    chrome_options.add_argument("--hide-scrollbars")
                    chrome_options.add_argument("--mute-audio")
                    chrome_options.add_argument("--no-default-browser-check")
                    chrome_options.add_argument("--no-first-run")
                    chrome_options.add_argument("--force-device-scale-factor=1")
                    chrome_options.add_argument("--disk-cache-dir=/dev/null")

                try:
                    self.logger.info("Attempting to initialize Chrome WebDriver via webdriver-manager.")
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info(f"Chrome WebDriver initialized via webdriver-manager (headless: {self.headless}).")
                    return driver
                except Exception as e:
                    self.logger.warning(f"webdriver-manager failed for Chrome: {e}. Falling back to local setup.")
                    self.logger.info("Attempting to initialize Chrome WebDriver using local setup (Selenium Manager).")
                    driver = webdriver.Chrome(options=chrome_options)
                    self.logger.info(f"Chrome WebDriver initialized via local setup (headless: {self.headless}).")
                    return driver
            elif self.browser == "firefox":
                firefox_options = FirefoxOptions()
                if self.headless:
                    firefox_options.add_argument("-headless")
                try:
                    service = FirefoxService(GeckoDriverManager().install())
                    driver = webdriver.Firefox(service=service, options=firefox_options)
                    self.logger.info(f"Firefox WebDriver initialized via webdriver-manager (headless: {self.headless}).")
                    return driver
                except Exception as e:
                    self.logger.warning(f"webdriver-manager failed for Firefox: {e}. Falling back to local setup.")
                    driver = webdriver.Firefox(options=firefox_options)
                    self.logger.info(f"Firefox WebDriver initialized (headless: {self.headless}).")
                    return driver
            elif self.browser == "edge":
                edge_options = EdgeOptions()
                if self.headless:
                    edge_options.add_argument("--headless")
                try:
                    service = EdgeService(EdgeChromiumDriverManager().install())
                    driver = webdriver.Edge(service=service, options=edge_options)
                    self.logger.info(f"Edge WebDriver initialized via webdriver-manager (headless: {self.headless}).")
                    return driver
                except Exception as e:
                    self.logger.warning(f"webdriver-manager failed for Edge: {e}. Falling back to local setup.")
                    driver = webdriver.Edge(options=edge_options)
                    self.logger.info(f"Edge WebDriver initialized (headless: {self.headless}).")
                    return driver
            elif self.browser == "safari":
                safari_options = SafariOptions()
                driver = webdriver.Safari(options=safari_options)
                self.logger.info("Safari WebDriver initialized (ensure remote automation is enabled).")
                return driver
            else:
                raise ValueError(f"Unsupported browser: {self.browser}.")
        except Exception as e:
            self.logger.error(f"Error initializing WebDriver: {e}")
            raise