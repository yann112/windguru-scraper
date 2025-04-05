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
        Formats the raw scraped forecast data into a structured dictionary.
        """
        dates = raw_forecast.get('date_info')
        if not dates:
            self.logger.warning("No date information found in the raw forecast.")
            return {}

        formatted_data = {}
        num_observations = len(dates)

        for i in range(num_observations):
            date_hour_str = self._parse_date_hour(dates[i])
            if date_hour_str:
                forecast_at_time = {}
                for item_name, config_item in config.items():
                    if item_name != 'date_info':
                        column_name = config_item.get('column_name', item_name)
                        if item_name in raw_forecast and len(raw_forecast[item_name]) > i:
                            value = raw_forecast[item_name][i]
                            if item_name == 'cloud_cover':
                                cloud_data = self._parse_cloud_cover(value)
                                forecast_at_time.update(cloud_data)
                            else:
                                forecast_at_time[column_name] = value
                formatted_data[date_hour_str] = forecast_at_time

        self.logger.info("Forecast data formatted.")
        return formatted_data