import configparser
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from dataclasses import asdict

import logging
import pandas as pd
from .extraction_strategies import ExtractionStrategyFactory
from .formater import ForecastFormatter

class WindguruMetadata:
    """
    A class to hold metadata about the Windguru forecast data.
    """
    column_metadata = {
        "wind_const_speed": {"description": "Average wind speed", "unit": "knots (kn)"},
        "gust_speed": {"description": "Maximum instantaneous wind speed (gust)", "unit": "knots (kn)"},
        "wind_dir": {"description": "Wind direction (meteorological convention)", "unit": "degrees (°)"},
        "swell_height": {"description": "Significant wave height of the primary swell", "unit": "meters (m)"},
        "swell_period": {"description": "Period of the primary swell", "unit": "seconds (s)"},
        "swell_direction": {"description": "Direction from which the primary swell is coming (oceanographic convention)", "unit": "degrees (°)"},
        "temperature": {"description": "Air temperature", "unit": "degrees Celsius (°C)"},
        "low_cloud_cover": {"description": "Percentage of low-level cloud cover", "unit": "percentage (%)"},
        "medium_cloud_cover": {"description": "Percentage of mid-level cloud cover", "unit": "percentage (%)"},
        "high_cloud_cover": {"description": "Percentage of high-level cloud cover", "unit": "percentage (%)"},
        "precipitation": {"description": "Precipitation amount", "unit": "millimeters (mm)"},
    }

    source_url = "https://www.windguru.cz/"

    datetime_format_explanation = (
        "The keys in the 'forecast' section represent the forecast time. "
        "The format is: 'DayAbbreviation-DayOfMonth-HourOfDayIn24hFormat' (e.g., 'Sa-5-08' for Saturday, the 5th of the month, at 08:00)."
    )
class LoggerManager:
    """
    A dedicated class for managing logging.
    """
    def __init__(self, logger_name=None):
        self.logger = logging.getLogger(logger_name or __name__)
        self.logger.setLevel(logging.INFO)

        # Create a console handler and set its level
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Create a formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        # Add the handler to the logger
        self.logger.addHandler(ch)

    def get_logger(self):
        return self.logger


class InitWebDriver:
    """
    A dedicated class for managing WebDriver initialization.
    """
    def __init__(self, url, browser="chrome", headless=True, logger=None):
        self.logger = logger or LoggerManager().get_logger()
        self.browser = browser.lower()
        self.url = url
        self.headless = headless

    def __call__(self):
        """
        Initializes and returns the appropriate WebDriver based on the browser type.
        """
        try:
            if self.browser == "chrome":
                chrome_options = ChromeOptions()
                if self.headless:
                    chrome_options.add_argument("--headless=new")  # Or "--headless" depending on Chrome version
                driver = webdriver.Chrome(options=chrome_options)
                self.logger.info(f"Chrome WebDriver initialized (headless: {self.headless}).")
            elif self.browser == "firefox":
                firefox_options = FirefoxOptions()
                if self.headless:
                    firefox_options.add_argument("-headless")
                driver = webdriver.Firefox(options=firefox_options)
                self.logger.info(f"Firefox WebDriver initialized (headless: {self.headless}).")
            elif self.browser == "edge":
                edge_options = EdgeOptions()
                if self.headless:
                    edge_options.add_argument("--headless")
                driver = webdriver.Edge(options=edge_options)
                self.logger.info(f"Edge WebDriver initialized (headless: {self.headless}).")
            elif self.browser == "safari":
                safari_options = SafariOptions()
                # Safari's headless mode is more complex and might not be directly supported
                driver = webdriver.Safari(options=safari_options)
                self.logger.info("Safari WebDriver initialized.")
            else:
                raise ValueError(f"Unsupported browser: {self.browser}. Use 'chrome' or 'firefox'.")
            return driver
        except Exception as e:
            self.logger.error(f"Error initializing WebDriver: {e}")
            raise


class ScraperWg:
    """
    A scraper class focused solely on scraping logic, configured by a JSON file,
    returning a dictionary-based forecast.
    """
    def __init__(
        self,
        config_path='../../scraping_config.ini',
        url='https://www.windguru.cz/',
        station_number=53,
        browser="chrome",
        logger=None
            ):
        self.station_number = station_number
        self.url = url + str(self.station_number)
        self.logger = logger or LoggerManager().get_logger()
        self.driver= InitWebDriver(browser=browser, logger=self.logger, url=url)()
        self.config = self._load_config(config_path)
        
        self.strategy_factory = ExtractionStrategyFactory(self.logger)
        self.formatter = ForecastFormatter(self.logger)
        self.metadata = WindguruMetadata()
        
        self._cached_forecast = None

    def print_forecast(self, output_format='human'):
        """
        Prints the already formatted weather forecast to the console.
        Args:
            output_format (str, optional): The desired output format.
                'human': Prints a human-readable table using pandas.
                'llm': Prints a JSON string of the formatted data.
                Defaults to 'human'.
        """
        if self._cached_forecast:
            if output_format.lower() == 'human':
                print("-------------------- Weather Forecast --------------------")
                print(f"Station Number: {self.station_number}")
                print(pd.DataFrame(self._cached_forecast).to_string())
            elif output_format.lower() == 'llm':
                llm_output = {
                    "description": f"Windguru weather forecast data from {self.metadata.source_url} with detailed column metadata below.",
                    "column_metadata": self.metadata.column_metadata,
                    "datetime_format": self.metadata.datetime_format_explanation,
                    "forecast": self._cached_forecast
                }
                print(json.dumps(llm_output, indent=2))
            else:
                print(f"Warning: Unknown output format '{output_format}'. Using human format.")
                print("-------------------- Weather Forecast --------------------")
                print(f"Station Number: {self.station_number}")
                print(pd.DataFrame(self._cached_forecast).to_string())
        else:
            print("No forecast data to print.")
    
    def get_formatted_forecast(self, num_prev=None):
        """
        Scrapes and formats the weather forecast.
        Args:
            num_prev (int, optional): Number of forecast observations to include.
        Returns:
            dict: The formatted forecast data, or None if scraping fails.
        """
        raw_forecast = self.scrape_raw(num_prev=num_prev)
        if raw_forecast:
            formated_forecast = self.formatter.format_forecast(raw_forecast, self.config)
            self._cached_forecast = formated_forecast
            return formated_forecast
        return None

    def scrape_raw(self, num_prev=None):
        """
        Only scrapes the raw data without formatting.
        """
        self.driver.get(self.url)
        self.logger.info("Starting raw data scraping...")
        self._wait_for_page_load()

        raw_forecast = {}
        for item_name, config in self.config.items():
            element_id = config.get('element_id')
            if element_id:
                try:
                    raw_data = self._extract_data(element_id, config)
                    raw_forecast[item_name] = self._limit_observations(raw_data, num_prev, item_name)
                    self.logger.info(f"Raw data scraped for '{item_name}'.")
                except Exception as e:
                    self.logger.warning(f"Error during raw data extraction for '{item_name}': {e}")
                    raw_forecast[item_name] = []
            else:
                self.logger.warning(f"Skipping '{item_name}': missing 'element_id'.")
        self.logger.info("Raw data scraping complete.")
        return raw_forecast
    
    def close_driver(self):
        """Closes the Selenium WebDriver."""
        if self.driver:
            self.driver.quit()
            self.logger.info("WebDriver closed.")

    def _limit_observations(self, raw_data, num_prev, item_name):
        """Limits the number of observations in the raw data if num_prev is provided."""
        if num_prev is not None:
            try:
                return raw_data[:int(num_prev)]
            except ValueError:
                self.logger.warning(f"Invalid 'num_prev' value: '{num_prev}'. Using all available data for '{item_name}'.")
                return raw_data
            except TypeError:
                self.logger.warning(f"'num_prev' is not a valid number: '{num_prev}'. Using all available data for '{item_name}'.")
                return raw_data
        return raw_data
    
    def _wait_for_page_load(self):
        """Waits for the page to load and returns True if successful, raises TimeoutException otherwise."""
        try:
            WebDriverWait(self.driver, 10).until(  # Increased timeout for potentially slow loading
                expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="tabid_0_0_dates"]/td[1]'))
            )
            self.logger.debug("Page loaded successfully.")
            return True
        except TimeoutException:
            self.logger.error("Timeout while waiting for the page to load.")
            raise TimeoutException("Failed to load the initial Windguru page.")

    def _extract_data(self, element_id, config_item):
        """
        Extracts data using the strategy pattern based on the configured extraction method.
        """
        try:
            row = self.driver.find_element(By.ID, element_id)
            target_tcell = config_item.get('target_tcell', True)
            cells_xpath = ".//td[contains(@class, 'tcell')]" if target_tcell else ".//td"
            cells = row.find_elements(By.XPATH, cells_xpath)
            extraction_method_name = config_item.get('extraction_method')
            strategy = self.strategy_factory.get_strategy(extraction_method_name, config_item)
            if strategy:
                return strategy.extract(cells)
            else:
                self.logger.warning(f"No extraction strategy found for method: {extraction_method_name}")
                return [cell.text.strip() for cell in cells] # Default fallback

        except Exception as e:
            self.logger.warning(f"Error during data extraction for '{element_id}': {e}")
            return []

    def _load_config(self, config_path="config.ini"):
        """Loads the scraping configuration from an INI file.

        Args:
            config_path (str): The path to the configuration file (default: config.ini).

        Returns:
            dict: A dictionary where keys are section names and values are dictionaries
                of the section's parameters. Returns an empty dictionary on error.
        """
        config = configparser.ConfigParser()
        try:
            if not os.path.exists(config_path):
                self.logger.error(f"Configuration file not found at: {config_path}")
                return {}
            config.read(config_path)
            config_data = {}
            for section in config.sections():
                config_data[section] = {}
                for key, value in config.items(section):
                    config_data[section][key] = value
            self.logger.info(f"Configuration loaded successfully from: {config_path}")
            return config_data
        except configparser.Error as e:
            self.logger.error(f"Error parsing configuration file '{config_path}': {e}")
            return {}
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while loading configuration from '{config_path}': {e}")
            return {}