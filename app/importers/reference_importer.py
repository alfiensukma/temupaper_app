import csv
from .base_importer import CSVDataImporter

class ReferenceImporter(CSVDataImporter):
    def import_data(self, driver):
        reference = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                reference.append({
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                })
        # Load the CSV file into Neo4j
        query = """
        UNWIND $reference AS row
        MATCH (source:Paper {paperId: row.source_id})
        MATCH (target:Paper {paperId: row.target_id})
        MERGE (source)-[:REFERENCES]->(target)
        """

        with driver.session() as session:
            session.run(query, reference=reference)