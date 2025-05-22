import csv
from .base_importer import CSVDataImporter

class ReferenceImporter(CSVDataImporter):
    def import_data(self, driver):
        reference = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            required_columns = ["source_id", "target_id"]
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing required columns: {missing_columns}")
            
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