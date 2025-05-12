import csv
from .base_importer import CSVDataImporter

class AuthorImporter(CSVDataImporter):
    def import_data(self, driver):
        papers = []
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                papers.append({
                    "paperId": row["paperId"],
                    "authors": row.get("authors", "[]")
                })

        query = """
        UNWIND $papers AS row
        MATCH (p:Paper {paperId: row.paperId})
        WITH p, apoc.convert.fromJsonList(row.authors) AS authors
        UNWIND authors AS author
        MERGE (a:Author {authorId: author.authorId})
        SET a.name = author.name
        MERGE (p)-[:AUTHORED_BY]->(a)
        """
        with driver.session() as session:
            session.run(query, papers=papers)