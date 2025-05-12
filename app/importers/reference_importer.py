import os
from .base_importer import CSVDataImporter

class ReferenceImporter(CSVDataImporter):
    def import_data(self, driver):
        query = f"""
        LOAD CSV WITH HEADERS FROM 'file:///{os.path.basename(self.file_path)}' AS row
        MATCH (source:Paper {{paperId: row.source_id}})
        MATCH (target:Paper {{paperId: row.target_id}})
        MERGE (source)-[:REFERENCES]->(target)
        """
        with driver.session() as session:
            session.run(query)