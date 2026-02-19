import json
import os
import logging

from util.jsonstore import JsonStore

logger = logging.getLogger(__name__)

class Settings(JsonStore):
    def __init__(self, filename='settings.json'):
        super().__init__(filename)

    def set(self, key, value):
        pass # read-only

settings = Settings()
