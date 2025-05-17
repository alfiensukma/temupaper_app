import csv
from .base_importer import CSVDataImporter

class InstitutionImporter(CSVDataImporter):
    def import_data(self, driver):
        institusi = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                institusi.append({
                    "names": row["universitas"],
                    "institutionId": row["no"],
                })

        query = """
        UNWIND $institusi AS row
        MERGE (pt:Institution {institutionId: row.institutionId})
        SET pt.names = row.names
        """
        with driver.session() as session:
            session.run(query, institusi=institusi)