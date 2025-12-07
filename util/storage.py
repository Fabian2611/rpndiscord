import json
import os
import logging

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, filename='storage.json'):
        self.filename = filename
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from {self.filename}. Starting with empty storage.")
                self.data = {}
        else:
            self.data = {}

    def save(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save storage to {self.filename}: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            self.save()
            return True
        return False

    def clear(self):
        self.data = {}
        self.save()
