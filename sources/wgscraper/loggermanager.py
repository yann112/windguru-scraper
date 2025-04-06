import logging

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