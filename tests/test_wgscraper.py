import pytest

from pathlib import Path
from wgscraper import ScraperWg

# Define a test URL
TEST_URL = "https://www.windguru.cz/"

def test_scrape_output_not_empty():
    """
    Test that the scraper returns a non-empty result.
    """
    # Get the path to the root directory
    root_path = Path(__file__).resolve().parent.parent

    # Construct the path to the config file
    config_path = root_path / 'scraping_config.ini'
    print(f"Attempting to load config from: {config_path}")

    with ScraperWg(
        config_path=str(config_path),  # Convert Path object to string
        url=TEST_URL,
        station_number=500968,
        browser="chrome",
    ) as scrapper :

        # Scrape a small number of forecasts
        num_prev = 20
        result = scrapper.get_formatted_forecast(num_prev)
    
        scrapper.print_forecast()
        scrapper.print_forecast(output_format="llm")

    # Check that the result is not None and is a dictionary (or your expected format)
    assert result is not None, "Scraping returned None"
    assert isinstance(result, dict), "Scraping result is not a dictionary"
    assert len(result) > 0, "Scraping returned an empty dictionary"