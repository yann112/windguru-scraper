import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import logging


class LoggerManager:
    """
    A dedicated class for managing logging.
    """
    def __init__(self, logger_name=None):
        self.logger = logging.getLogger(logger_name or __name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create a console handler and set its level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        
        # Create a formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        
        # Add the handler to the logger
        self.logger.addHandler(ch)

    def get_logger(self):
        return self.logger


class WebDriverManager:
    """
    A dedicated class for managing WebDriver initialization.
    """
    def __init__(self, browser="chrome", logger=None):
        self.logger = logger or LoggerManager().get_logger()
        self.browser = browser.lower()

    def initialize_driver(self):
        """
        Initializes and returns the appropriate WebDriver based on the browser type.
        """
        try:
            if self.browser == "chrome":
                driver = webdriver.Chrome(ChromeDriverManager().install())
                self.logger.info("Chrome WebDriver initialized.")
            elif self.browser == "firefox":
                driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
                self.logger.info("Firefox WebDriver initialized.")
            else:
                raise ValueError(f"Unsupported browser: {self.browser}. Use 'chrome' or 'firefox'.")
            return driver
        except Exception as e:
            self.logger.error(f"Error initializing WebDriver: {e}")
            raise


class ScraperWg:
    """
    A scraper class focused solely on scraping logic.
    """
    def __init__(self, url, browser="chrome", logger=None):
        self.url = url
        self.logger = logger or LoggerManager().get_logger()
        self.driver_manager = WebDriverManager(browser=browser, logger=self.logger)
        self.driver = self.driver_manager.initialize_driver()
        self.driver.get(self.url)
        self.logger.info(f"Browser opened and navigated to {self.url}")

    def scrape(self, num_prev):
        """
        Scrapes a specified number of weather forecasts.
        Args:
            num_prev: Number of forecast observations to scrape.
        Returns:
            A pandas DataFrame containing the scraped forecast data.
        """
        self.logger.info("Starting the scraping process...")
        
        # Wait for the page to load before scraping
        if not self._wait_for_page_load():
            return None

        # Extract data
        forecast = {}
        forecast['date'] = self._extract_dates(num_prev)
        for name in ['tabid_0_0_WINDSPD', 'tabid_0_0_GUST', 'tabid_0_0_HTSGW', 'tabid_0_0_PERPW']:
            forecast[name] = self._extract_numeric_figures(name, num_prev)
        for name in ['tabid_0_0_SMER', 'tabid_0_0_DIRPW']:
            forecast[name] = self._extract_angles(name, num_prev)

        # Format and clean the data
        forecast_df = self._format_forecast_data(forecast)
        self.logger.info("Weather forecasts scraped successfully.")
        return forecast_df

    def _wait_for_page_load(self):
        """Waits for the page to load and returns True if successful."""
        try:
            WebDriverWait(self.driver, 5).until(
                expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="tabid_0_0_dates"]/td[1]'))
            )
            self.logger.debug("Page loaded successfully.")
            return True
        except TimeoutException:
            self.logger.error("Timeout while waiting for the page to load.")
            return False

    def _extract_dates(self, num_prev):
        """Extracts date information from the page."""
        temp_list = []
        for i in range(1, int(num_prev) + 1):
            try:
                value = self.driver.find_element(By.XPATH, f'//*[@id="tabid_0_0_dates"]/td[{i}]')
                temp_list.append(value.text)
            except Exception as e:
                self.logger.warning(f"Error extracting date at index {i}: {e}")
                temp_list.append(pd.NA)
        return temp_list

    def _extract_numeric_figures(self, name, num_prev):
        """Extracts numeric figures (e.g., wind speed, swell height) from the page."""
        temp_list = []
        for i in range(1, int(num_prev) + 1):
            try:
                value = self.driver.find_element(By.XPATH, f'//*[@id="{name}"]/td[{i}]')
                text_value = value.text.strip()
                numeric_value = float(text_value) if text_value else 0.0
                temp_list.append(numeric_value)
            except Exception as e:
                self.logger.warning(f"Error extracting numeric figure for {name} at index {i}: {e}")
                temp_list.append(pd.NA)
        return temp_list

    def _extract_angles(self, name, num_prev):
        """Extracts angle information (e.g., wind direction, swell direction) from the page."""
        parse_number = lambda x: int(''.join([l for l in str(x) if l.isdigit()]))
        temp_list = []
        for i in range(1, int(num_prev) + 1):
            try:
                value = self.driver.find_element(By.XPATH, f'//*[@id="{name}"]/td[{i}]/span')
                numeric_value = parse_number(value.get_attribute('title'))
                temp_list.append(numeric_value)
            except Exception as e:
                self.logger.warning(f"Error extracting angle for {name} at index {i}: {e}")
                temp_list.append(0)
        return temp_list

    def _format_forecast_data(self, forecast):
        """Formats the raw forecast data into a structured pandas DataFrame."""
        forecast_df = pd.DataFrame(forecast)

        # Split and reformat date column
        forecast_df['day'] = forecast_df['date'].str.split('\n').str[0]
        forecast_df['number_day'] = forecast_df['date'].str.split('\n').str[1].str.split('.').str[0]
        forecast_df['hour'] = forecast_df['date'].str.split('\n').str[2].str.replace('h', '')

        # Clean and drop unnecessary columns
        forecast_df.replace('', pd.NA, inplace=True)
        forecast_df.drop(columns=['date'], inplace=True)
        forecast_df.dropna(inplace=True)

        # Map day abbreviations
        day_mapping = {'Mo': 'Lun', 'Tu': 'Mar', 'We': 'Mer', 'Th': 'Jeu', 'Fr': 'Ven', 'Sa': 'Sam', 'Su': 'Dim'}
        forecast_df['day'] = forecast_df['day'].map(day_mapping)

        # Rename and reorder columns
        forecast_df.columns = [
            'wind_const_speed', 'gust_speed', 'swell_height', 'swell_period', 'wind_dir', 'swell_dir',
            'day', 'number_day', 'hour'
        ]
        forecast_df = forecast_df[
            ['day', 'number_day', 'hour', 'wind_const_speed', 'gust_speed', 'swell_height', 'swell_period', 'wind_dir', 'swell_dir']
        ]

        # Add derived columns
        forecast_df['wind_speed'] = forecast_df[['wind_const_speed', 'gust_speed']].mean(axis=1)
        forecast_df[
            ['wind_speed', 'swell_period', 'number_day', 'hour', 'wind_const_speed', 'gust_speed']
        ] = forecast_df[
            ['wind_speed', 'swell_period', 'number_day', 'hour', 'wind_const_speed', 'gust_speed']
        ].astype(int)

        # Filter hours between 7 and 21
        forecast_df = forecast_df[forecast_df['hour'] >= 7]
        forecast_df = forecast_df[forecast_df['hour'] <= 21]

        # Add arrow directions
        forecast_df['arrow_wind_dir'] = forecast_df['wind_dir'].apply(lambda x: (x + 180) % 360)
        forecast_df['arrow_swell_dir'] = forecast_df['swell_dir'].apply(lambda x: (x + 180) % 360)

        return forecast_df


# Main part of the script for testing
if __name__ == "__main__":
    # Example URL for testing
    test_url = "https://www.windguru.cz/53"

    # Instantiate the scraper with automatic WebDriver detection
    scraper = ScraperWg(test_url, browser="chrome")  # Change to "firefox" if needed

    # Scrape 10 forecasts as an example
    forecast_data = scraper.scrape(10)

    # Display the scraped data
    if forecast_data is not None:
        print(forecast_data)