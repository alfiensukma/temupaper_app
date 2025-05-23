import ast
import csv
from .base_importer import CSVDataImporter
import logging
logger = logging.getLogger(__name__)
class PaperImporter(CSVDataImporter):
    def __init__(self, file_path, is_reference=False):
        super().__init__(file_path)
        self.is_reference = is_reference
        self.logger = logging.getLogger(__name__)

    def import_data(self, driver):
        papers = []
        self.logger.info(f"Reading CSV file: {self.file_path}")
        
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Validasi kolom yang dibutuhkan
            required_columns = ["paperId", "title", "abstract", "embedding"]
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing required columns: {missing_columns}")

            for row in reader:
                self.logger.debug(f"Processing paperId: {row['paperId']}")
                external_ids_str = row.get("externalIds", "{}")
                try:
                    external_ids = ast.literal_eval(external_ids_str)
                    doi = external_ids.get("DOI", "")
                except Exception as e:
                    self.logger.warning(f"Failed to parse externalIds for paperId {row['paperId']}: {str(e)}")
                    doi = ""

                papers.append({
                    "paperId": row["paperId"],
                    "corpusId": row.get("corpusId", ""),
                    "doi": doi,
                    "title": row.get("title", ""),
                    "year": row.get("year", ""),
                    "abstract": row.get("abstract", ""),
                    "url": row.get("url", ""),
                    "publicationDate": row.get("publicationDate", ""),
                    "venue": row.get("venue", ""),
                    "citationCount": row.get("citationCount", ""),
                    "influentialCitationCount": row.get("influentialCitationCount", ""),
                    "embedding": row.get("embedding", ""),
                    "referenceCount": row.get("referenceCount", ""),
                })

        query = """
        UNWIND $papers AS row
        MERGE (p:Paper {paperId: row.paperId})
        SET p.corpusId = row.corpusId,
            p.doi = row.doi,
            p.title = row.title,
            p.year = toInteger(row.year),
            p.abstract = row.abstract,
            p.url = row.url,
            p.publicationDate = row.publicationDate,
            p.venue = row.venue,
            p.citationCount = toInteger(row.citationCount),
            p.influentialCitationCount = toInteger(row.citationCount),
            p.embedding = apoc.convert.fromJsonList(row.embedding),
            p.referenceCount = toInteger(row.referenceCount)
        """
        with driver.session() as session:
            session.run(query, papers=papers)