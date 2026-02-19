import json
import logging

logger = logging.getLogger(__name__)

class JsonStore:
    def __init__(self, filename: str):
        self.filename = filename
        self._data: dict = {}
        self._dirty = False
        self.load()

    def load(self):
        try:
            with open(self.filename) as f:
                self._data = json.load(f)
        except FileNotFoundError:
            self._data = {}
        except json.JSONDecodeError:
            logger.error(f"Corrupt JSON in {self.filename}, starting fresh")
            self._data = {}

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self._data, f, indent=2)
        self._dirty = False

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._dirty = True

    def delete(self, key):
        self._data.pop(key, None)
        self._dirty = True
