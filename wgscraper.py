import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import TimeoutException

class ScraperWg:

    def __init__(self, url):
        self.url = url
        self.driver = webdriver.Chrome()
        self.driver.get(self.url)

    def scrape(self, num_prev):

        """
        Scrapes a specified number of weather forecasts.
        Args:
        * num_prev: Number of forecast observations to scrape.
        Returns:
        * A pandas DataFrame containing the scraped forecast data:
            - Date & hour of estimate
            - Wind and gust speed and direction
            - Swell height, period and direction
        """

        # Wait for the browsed page before scraping
        try:
            myElem = WebDriverWait(self.driver, 5).until(expected_conditions.presence_of_element_located((By.XPATH, '//*[@id="tabid_0_0_dates"]/td[1]')))
        except TimeoutException:
            None

        # The forecast dict will store the scraped forecast
        forecast = {}

        # Extract datetime
        temp_list = []
        for i in range(1, int(num_prev) + 1):
            try:
                value = self.driver.find_element(By.XPATH, f'//*[@id="tabid_0_0_dates"]/td[{i}]')
                temp_list.append(value.text)
            except Exception as e:
                temp_list.append(pd.NA)
        forecast['date'] = temp_list

        # Extract numeric figures
        for name in ['tabid_0_0_WINDSPD','tabid_0_0_GUST','tabid_0_0_HTSGW', 'tabid_0_0_PERPW'] :
            temp_list = []
            for i in range(1, int(num_prev) + 1):
                try:
                    value = self.driver.find_element(By.XPATH, f'//*[@id="{name}"]/td[{i}]')
                    text_value = value.text.strip()
                    if text_value == '' or text_value.isspace():
                        numeric_value = float(0.0)
                    else:
                        numeric_value = float(text_value)
                    temp_list.append(numeric_value)
                except Exception as e:
                    temp_list.append(pd.NA)
            forecast[name] = temp_list

        # Extract numeric figures from angles
        parse_number = lambda x: int(''.join([l for l in str(x) if l.isdigit()]))

        # Extract angles
        for name in ['tabid_0_0_SMER','tabid_0_0_DIRPW']:
            temp_list = []
            for i in range(1, int(num_prev) + 1):
                try:
                    value = self.driver.find_element(By.XPATH, f'//*[@id="{name}"]/td[{i}]/span')
                    numeric_value = parse_number(value.get_attribute('title'))
                    temp_list.append(numeric_value)
                except Exception as e:
                    temp_list.append(0)
            forecast[name] = temp_list

        forecast_df=pd.DataFrame(forecast)

        # Formatting

        forecast_df['day'] = forecast_df['date'].str.split('\n').str[0]
        forecast_df['number_day'] = forecast_df['date'].str.split('\n').str[1].str.split('.').str[0]
        forecast_df['hour'] = forecast_df['date'].str.split('\n').str[2].str.replace('h', '')

        forecast_df.replace('', pd.NA, inplace=True)
        forecast_df.drop(columns=['date'], inplace=True)
        forecast_df.dropna(inplace=True)

        day_mapping = {'Mo': 'Lun','Tu': 'Mar','We': 'Mer','Th': 'Jeu','Fr': 'Ven','Sa': 'Sam','Su': 'Dim'}
        forecast_df['day'] = forecast_df['day'].map(day_mapping)

        forecast_df.columns = ['wind_const_speed','gust_speed','swell_height','swell_period','wind_dir','swell_dir','day','number_day', 'hour']
        forecast_df = forecast_df[['day','number_day', 'hour', 'wind_const_speed','gust_speed','swell_height','swell_period','wind_dir','swell_dir']]
        forecast_df['wind_speed'] = forecast_df[['wind_const_speed', 'gust_speed']].mean(axis=1)
        forecast_df[['wind_speed','swell_period', 'number_day', 'hour', 'wind_const_speed', 'gust_speed']] = forecast_df[['wind_speed','swell_period', 'number_day', 'hour', 'wind_const_speed', 'gust_speed']].astype(int)

        forecast_df = forecast_df[forecast_df['hour'] >= 7]
        forecast_df = forecast_df[forecast_df['hour'] <= 21]

        forecast_df['arrow_wind_dir'] = forecast_df['wind_dir'].apply(lambda x: (x+180)%360)
        forecast_df['arrow_swell_dir'] = forecast_df['swell_dir'].apply(lambda x: (x+180)%360)

        print("✅ Weather forecasts scraped")

        return forecast_df
