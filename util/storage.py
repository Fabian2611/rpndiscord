import json
import os
import logging

from util.jsonstore import JsonStore

logger = logging.getLogger(__name__)

class Storage(JsonStore):
    def __init__(self, filename='storage.json'):
        super().__init__(filename)

    def set(self, key, value):
        super().set(key, value)
        self.save()
