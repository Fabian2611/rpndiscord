import json
import os
import logging

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self, filename='settings.json'):
        self.filename = filename
        self.config = {}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.config = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from {self.filename}")
                self.config = {}
        else:
            logger.warning(f"{self.filename} not found.")
            self.config = {}

    def get(self, key, default=None):
        return self.config.get(key, default)

settings = Settings()
