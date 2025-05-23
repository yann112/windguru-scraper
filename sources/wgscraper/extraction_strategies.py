from abc import ABC, abstractmethod
import json
import re
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By

    
class ExtractionStrategy(ABC):
    def __init__(self, config_item, logger):
        self.config_item = config_item
        self.logger = logger

    @abstractmethod
    def extract(self, cells: list[WebElement]) -> list:
        pass


class ExtractionStrategyFactory:
    def __init__(self, logger):
        self.logger = logger
        self.strategies = {
            'numeric_content': NumericContentStrategy,
            'text_content': TextContentStrategy,
            'angle_title_attribute': AngleTitleAttributeStrategy,
            'multi_div_text': MultiDivTextStrategy,
            'regex': RegexContentStrategy,
            'tide_combined': TideCombinedStrategy
        }

    def get_strategy(self, method_name: str, config_item: dict) -> ExtractionStrategy | None:
        strategy_class = self.strategies.get(method_name)
        if strategy_class:
            return strategy_class(config_item, self.logger)
        self.logger.warning(f"No extraction strategy found for method: {method_name}")
        return None
    

class NumericContentStrategy(ExtractionStrategy):
    def extract(self, cells: list[WebElement]) -> list:
        return [
            float(cell.text.strip()) if cell.text.strip() else None
            for cell in cells
        ]


class TextContentStrategy(ExtractionStrategy):
    def extract(self, cells: list[WebElement]) -> list:
        return [cell.text.strip() for cell in cells]


class AngleTitleAttributeStrategy(ExtractionStrategy):
    def extract(self, cells: list[WebElement]) -> list:
        param_value = self.config_item.get('param')
        span_xpath = self.config_item.get('span_xpath', ".//span[@title]")
        extracted_data = []
        if param_value:
            for cell in cells:
                data_x = cell.get_attribute("data-x")
                angle = None
                if data_x:
                    try:
                        data_x_json = json.loads(data_x)
                        param = data_x_json.get("param")
                        if param == param_value:
                            try:
                                span_element = cell.find_element(By.XPATH, span_xpath)
                                title_attribute = span_element.get_attribute("title")
                                if title_attribute:
                                    angle = int(title_attribute.split('(')[1].split('°)')[0])
                            except Exception as e:
                                self.logger.warning(f"Error extracting angle from title: {e}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"Error decoding data-x attribute: {data_x}")
                extracted_data.append(angle)
        else:
            self.logger.warning(f"Missing 'param' in config for angle extraction.")
        return extracted_data


class MultiDivTextStrategy(ExtractionStrategy):
    def extract(self, cells: list[WebElement]) -> list:
        div_selector = self.config_item.get('div_selector')
        extracted_data = []
        if div_selector:
            for cell in cells:
                divs = cell.find_elements(By.XPATH, div_selector)
                cloud_values = []
                for div in divs:
                    text = div.text.strip()
                    if text and text != '\xa0':
                        cloud_values.append(text)
                    else:
                        cloud_values.append(None)
                extracted_data.append("\n".join(map(str, cloud_values)))
        else:
            self.logger.warning(f"Missing 'div_selector' in config.")
            extracted_data = [cell.text.strip() for cell in cells]
        return extracted_data
    
class RegexContentStrategy(ExtractionStrategy):
    def extract(self, cells: list[WebElement]) -> list:
        pattern = self.config_item.get('pattern')
        group_names = self.config_item.get('group_names')
        extracted_data = []
        if pattern:
            for cell in cells:
                text = cell.text.strip()
                match = re.search(pattern, text)
                if match:
                    if group_names:
                        extracted_data.append(dict(zip(group_names, match.groups())))
                    elif match.groups():
                        extracted_data.append(match.groups() if len(match.groups()) > 1 else match.group(1))
                    else:
                        extracted_data.append(match.group(0))  # Return the whole match if no groups
                else:
                    extracted_data.append(None)
        else:
            self.logger.warning(f"Missing 'pattern' in config for regex extraction.")
            extracted_data = [None] * len(cells)
        return extracted_data

class TideCombinedStrategy(ExtractionStrategy):
    def extract(self, cells: list[WebElement]) -> list:
        pattern = self.config_item.get('pattern', r'(\d{2}:\d{2})')
        threshold = self.config_item.get('threshold', 5)
        extracted_data = []
        
        for cell in cells:
            # Find all SVG text elements in the cell
            text_elements = cell.find_elements(By.XPATH, ".//*[local-name()='text']")
            # Sort by X position for chronological order
            sorted_texts = sorted(text_elements, key=lambda e: int(e.get_attribute('x')))
            
            tides = []
            for elem in sorted_texts:
                time_match = re.search(pattern, elem.text)
                if time_match:
                    y = elem.get_attribute('y')
                    tide_type = 'low' if (y and int(y) > threshold) else 'high'
                    tides.append({
                        'time': time_match.group(1),
                        'type': tide_type
                    })
            extracted_data.append(tides)
        
        return extracted_data