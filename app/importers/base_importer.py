from abc import ABC, abstractmethod
import csv
import os

class CSVDataImporter(ABC):
    def __init__(self, file_path):
        self.file_path = file_path
        self.validate_file()

    def validate_file(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File {self.file_path} not found")

    def count_rows(self):
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            return sum(1 for row in csv.DictReader(f))

    @abstractmethod
    def import_data(self, driver):
        pass