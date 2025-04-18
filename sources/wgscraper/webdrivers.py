import logging
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
                    chrome_options.add_argument("--headless=new")
                try:
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    self.logger.info(f"Chrome WebDriver initialized via webdriver-manager (headless: {self.headless}).")
                    return driver
                except Exception as e:
                    self.logger.warning(f"webdriver-manager failed for Chrome: {e}. Falling back to local setup.")
                    driver = webdriver.Chrome(options=chrome_options)
                    self.logger.info(f"Chrome WebDriver initialized (headless: {self.headless}).")
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