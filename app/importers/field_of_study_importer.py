import logging
import csv
from .base_importer import CSVDataImporter

class FieldOfStudyImporter(CSVDataImporter):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.logger = logging.getLogger(__name__)

    def import_data(self, driver):
        fields = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                s2_fields = row.get("s2FieldsOfStudy", "")
                if s2_fields:
                    try:
                        fields_list = s2_fields.split(";")
                        for field in fields_list:
                            if field:
                                fields.append({
                                    "paperId": row["paperId"],
                                    "fieldName": field.strip()
                                })
                    except Exception as e:
                        self.logger.warning(f"Error processing s2FieldsOfStudy for paperId {row['paperId']}: {e}")

        query = """
        UNWIND $fields AS row
        MERGE (f:FieldOfStudy {name: row.fieldName})
        WITH f, row
        MATCH (p:Paper {paperId: row.paperId})
        MERGE (p)-[:HAS_FIELD]->(f)
        """
        with driver.session() as session:
            session.run(query, fields=fields)