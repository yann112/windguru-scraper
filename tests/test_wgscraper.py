import pytest

from wgscraper import ScraperWg

# Define a test URL (replace with a real URL or mock it)
TEST_URL = "https://www.windguru.cz/53"

def test_scrape_output_not_empty():
    """
    Test that the scraper returns a non-empty DataFrame.
    """
    # Instantiate the scraper
    scraper = ScraperWg(TEST_URL, browser="chrome")

    # Scrape a small number of forecasts (e.g., 5)
    num_prev = 5
    result_df = scraper.scrape(num_prev)

    # Check that the result is not None and is a non-empty DataFrame
    assert result_df is not None, "Scraping returned None"
    assert not result_df.empty, "Scraped DataFrame is empty"