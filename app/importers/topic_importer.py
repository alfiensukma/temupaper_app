import csv
import logging
from .base_importer import CSVDataImporter

class TopicImporter(CSVDataImporter):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.logger = logging.getLogger(__name__)

    def import_data(self, driver):
        topics = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic_id = row.get("topicId")
                topic_name = row.get("topic")
                if topic_id and topic_name:
                    topics.append({
                        "topicId": topic_id,
                        "topic": topic_name
                    })

        query = """
        UNWIND $topics AS row
        MERGE (t:Topic {topicId: row.topicId})
        SET t.name = row.topic
        """
        with driver.session() as session:
            session.run(query, topics=topics)

    def count_rows(self):
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            return sum(1 for _ in f) - 1  # minus header