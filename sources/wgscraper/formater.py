import logging

class ForecastFormatter:
    """
    A formatter class responsible for taking raw scraped data and
    formatting it into a structured forecast dictionary.
    """
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def _parse_date_hour(self, date_str):
        parts = date_str.split('\n')
        if len(parts) == 3:
            day_abbr, day_num_part, hour_part = parts
            day_str = day_num_part.replace('.', '').strip()
            hour_str = hour_part.replace('h', '').strip()
            return f"{day_abbr}-{day_str}-{hour_str}"
        else:
            self.logger.warning(f"Could not parse date string: {date_str}")
            return None

    def _parse_cloud_cover(self, cloud_cover_str):
        """Parses the cloud cover string into low, medium, and high percentages."""
        low = None
        medium = None
        high = None

        if isinstance(cloud_cover_str, str):
            parts = [p.strip() for p in cloud_cover_str.split('\n')]
            parsed_parts = []
            for part in parts:
                if part.isdigit():
                    parsed_parts.append(int(part))
                elif part.lower() == 'none':
                    parsed_parts.append(None)
                else:
                    self.logger.warning(f"Could not parse cloud cover part: '{part}'")
                    parsed_parts.append(None)

            if parsed_parts:
                high = parsed_parts[0] if len(parsed_parts) > 0 else None
                medium = parsed_parts[1] if len(parsed_parts) > 1 else None
                low = parsed_parts[2] if len(parsed_parts) > 2 else None

        return {'low_cloud_cover': low, 'medium_cloud_cover': medium, 'high_cloud_cover': high}

    def format_forecast(self, raw_forecast, config):
        """
        Formats the raw scraped forecast data (nested under "models")
        using model-specific configurations.
        """
        formatted_output = {'models': {}}
        models_data = raw_forecast.get('models', {})

        if not models_data:
            self.logger.warning("No 'models' key found in the raw forecast or it's empty.")
            return {}

        for model_name, model_forecast in models_data.items():
            model_config = config.get('models').get(model_name)
            if not model_config or 'columns' not in model_config:
                self.logger.warning(f"No valid configuration found for model: {model_name}")
                continue

            columns_config = model_config['columns']

            self.logger.info(f"Processing forecast data for model: {model_name}")
            dates = model_forecast.get('date_info')
            if not dates:
                self.logger.warning(f"No date information found for model: {model_name}")
                continue

            formatted_data = {}
            num_observations = len(dates)

            for i in range(num_observations):
                date_hour_str = self._parse_date_hour(dates[i])
                if date_hour_str:
                    forecast_at_time = {}
                    for item_name in columns_config:
                        if item_name != 'date_info':
                            column_name = columns_config.get('column_name', item_name)
                            if item_name in models_data[model_name] and len(models_data[model_name] [item_name]) > i:
                                value = models_data[model_name] [item_name][i]
                                if item_name == 'cloud_cover':
                                    cloud_data = self._parse_cloud_cover(value)
                                    forecast_at_time.update(cloud_data)
                                else:
                                    forecast_at_time[column_name] = value
                    formatted_data[date_hour_str] = forecast_at_time

            formatted_output['models'][model_name] = formatted_data
            self.logger.info(f"Forecast data formatted for model: {model_name}")

        return formatted_output