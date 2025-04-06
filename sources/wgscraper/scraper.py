import json
import os
import logging

import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException

from .webdrivers import InitWebDriver
from .extraction_strategies import ExtractionStrategyFactory
from .formater import ForecastFormatter
from .loggermanager import LoggerManager

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
class ScraperWg:
    """
    A simplified scraper class focused on the 'wg_model' table.
    """
    def __init__(
        self,
        config_path='../../scraping_config.json',
        url='https://www.windguru.cz/',
        station_number=53,
        browser="chrome",
        headless_browser = True,
        logger=None
            ):

        self.station_number = station_number
        self.url = url + str(self.station_number)
        self.logger = logger or LoggerManager().get_logger()

        self.config = self._load_config(config_path)

        self.driver= InitWebDriver(browser=browser, logger=self.logger, url=url, headless=headless_browser)()
        self.strategy_factory = ExtractionStrategyFactory(self.logger)
        self.formatter = ForecastFormatter(self.logger)
        self.metadata = WindguruMetadata()

        self._cached_raw_data = {}
        self._cached_formatted_forecast = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_driver()

    def print_forecast(self):
        if self._cached_formatted_forecast:
                llm_output = {
                    "description": f"Windguru weather and station data from {self.url} with detailed metadata.",
                    "column_metadata": self.metadata.column_metadata,
                    "datetime_format": self.metadata.datetime_format_explanation,
                    "data": self._cached_formatted_forecast
                }
                print(json.dumps(llm_output, indent=2))

        else:
            print("No data to print.")

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
            self._cached_formatted_forecast= formated_forecast
            return formated_forecast
        return None

    def scrape_raw(self, num_prev=None):
        self.driver.get(self.url)
        self.logger.info("Starting raw data scraping...")
        self._wait_for_page_load()

        raw_data = {"models": {}, "main_page_info": {}}

        # Scrape models data
        models_config = self.config.get('models', {})
        for model_name, model_config in models_config.items():
            if model_config.get('type') == 'table':
                location_config = model_config.get('location')
                columns_config = model_config.get('columns', {})

                if location_config and location_config.get('type') == 'id' and location_config.get('value'):
                    table_id = location_config.get('value')
                    self.logger.info(f"Scraping raw data for model '{model_name}' from table ID '{table_id}'...")
                    raw_data['models'][model_name] = self._extract_from_table(self.driver, table_id, columns_config, num_prev)
                    self.logger.info(f"Raw data scraping complete for model '{model_name}'.")
                else:
                    self.logger.warning(f"Invalid or missing 'location' configuration for model '{model_name}'.")
            else:
                self.logger.warning(f"No configuration found or it's not of type 'table' for model '{model_name}'.")

        # Scrape main page information
        main_page_config = self.config.get('main_page_data', {})
        if main_page_config:
            self.logger.info("Scraping main page information using external method...")
            raw_data['main_page_info'] = self._extract_main_page_info(self.driver, main_page_config)
            self.logger.info("Main page information scraping complete.")

        self._cached_raw_data = raw_data
        return raw_data

    def _extract_from_table(self, driver, table_id, columns_config, num_prev):
        table_data = {}
        for item_name, column_options in columns_config.items():
            element_id_suffix = column_options.get('element_id_suffix')
            cell_selector = column_options.get('cell_selector', ".//td") # Default to all td elements

            if element_id_suffix:
                try:
                    row = driver.find_element(By.ID, table_id + element_id_suffix)
                    cells = row.find_elements(By.XPATH, cell_selector)
                    extraction_method_name = column_options.get('extraction_method')
                    strategy = self.strategy_factory.get_strategy(extraction_method_name, column_options)
                    if strategy:
                        table_data[item_name] = self._limit_observations(strategy.extract(cells), num_prev, item_name)
                    else:
                        self.logger.warning(f"No extraction strategy found for method: {extraction_method_name}")
                        table_data[item_name] = self._limit_observations([cell.text.strip() for cell in cells], num_prev, item_name)
                    self.logger.info(f"Raw data scraped for column '{item_name}'.")
                except Exception as e:
                    self.logger.warning(f"Error during raw data extraction for column '{item_name}': {e}")
                    table_data[item_name] = []
            else:
                self.logger.warning(f"Skipping column '{item_name}': missing 'element_id_suffix'.")
        return table_data
    
    def _extract_main_page_info(self, driver, main_page_config):
        extracted_data = {}

        for item_name, item_config in main_page_config.items():
            location_config = item_config.get('location')
            extraction_config = item_config.get('extraction')

            if location_config and location_config.get('type') and location_config.get('value') and extraction_config and extraction_config.get('method'):
                location_type = location_config['type']
                location_value = location_config['value']
                extraction_method = extraction_config['method']

                element = None
                try:
                    if location_type == 'css_selector':
                        element = driver.find_element(By.CSS_SELECTOR, location_value)
                    elif location_type == 'xpath':
                        element = driver.find_element(By.XPATH, location_value)
                    else:
                        self.logger.warning(f"Unsupported location type '{location_type}' for '{item_name}'.")
                        continue

                    if element:
                        strategy = self.strategy_factory.get_strategy(extraction_method, extraction_config)
                        if strategy:
                            # For single element extraction, we'll treat it as a list of one
                            extracted_value = strategy.extract([element])
                            if extracted_value:
                                extracted_data[item_name] = extracted_value[0] if len(extracted_value) == 1 else extracted_value
                                self.logger.info(f"Extracted '{item_name}': {extracted_data[item_name]}")
                            else:
                                self.logger.warning(f"Extraction strategy returned empty result for '{item_name}'.")
                        else:
                            self.logger.warning(f"No valid extraction strategy found for '{item_name}'.")

                except Exception as e:
                    self.logger.error(f"An error occurred while extracting '{item_name}': {e}")
            else:
                self.logger.warning(f"Invalid or missing configuration for main page item '{item_name}'.")
        return extracted_data

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed.")
                self.driver = None
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")

    def _limit_observations(self, raw_data, num_prev, item_name):
        if num_prev is not None:
            try:
                return raw_data[:int(num_prev)]
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid 'num_prev' value: '{num_prev}'. Using all available data for '{item_name}'.")
        return raw_data

    def _wait_for_page_load(self):
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located((By.ID, 'tabid_0_0_dates'))
            )
            self.logger.debug("Page loaded successfully.")
            return True
        except TimeoutException:
            self.logger.error("Timeout while waiting for the page to load.")
            raise TimeoutException("Failed to load the initial Windguru page.")

    def _load_config(self, config_path="config.json"):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            self.logger.info(f"Configuration loaded successfully from: {config_path}")
            return config_data
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found at: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON configuration file '{config_path}': {e}")
            raise ValueError(f"Failed to parse config file: {config_path}") from e
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while loading configuration from '{config_path}': {e}")
            raise ValueError(f"Failed to load config file: {config_path}") from e