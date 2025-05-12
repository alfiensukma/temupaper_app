import logging
import csv
from .base_importer import CSVDataImporter

class PublicationTypeImporter(CSVDataImporter):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.logger = logging.getLogger(__name__)

    def import_data(self, driver):
        papers_data = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pub_types = row.get("publicationTypes", "")
                try:
                    if isinstance(pub_types, str):
                        types_list = pub_types.split(";")
                        for type_name in types_list:
                            if type_name:
                                papers_data.append({
                                    "paperId": row["paperId"],
                                    "typeName": type_name.strip()
                                })
                except Exception as e:
                    self.logger.warning(f"Error processing publicationTypes for paperId {row['paperId']}: {e}")

        query = """
        UNWIND $papers as row
        MERGE (pt:PublicationType {name: row.typeName})
        WITH pt, row
        MATCH (p:Paper {paperId: row.paperId})
        MERGE (p)-[:HAS_TYPE]->(pt)
        """
        with driver.session() as session:
            session.run(query, papers=papers_data)