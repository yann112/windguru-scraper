# windguru-scraper
Python script that scrapes weather forecast from Windguru using Selenium 

Input: 
- URL of the page to scrape (var 'url')
- Number of previsions to scrape (var 'num_prev')

Output: 
- Scraped forecasts (wind speed, wind direction, wind gusts, swell height, swell period, wind direction, swell direction) in a pd.DataFrame

Requirements:
- Python 3.10.6
- Pandas version 2.2.2
- Selenium version 4.22.0
- ChromeDriver
