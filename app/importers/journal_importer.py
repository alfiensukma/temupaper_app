import csv
import json
import logging
from .base_importer import CSVDataImporter

class JournalImporter(CSVDataImporter):
    def __init__(self, file_path, is_relation=False):
        super().__init__(file_path)
        self.is_relation = is_relation
        self.logger = logging.getLogger(__name__)

    def import_data(self, driver):
        if not self.is_relation:
            journals = []
            with open(self.file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    issn = row.get("Issn", "")
                    issn_list = issn.split(", ")
                    for issn in issn_list:
                        journals.append({
                            "title": row["Title"],
                            "sjr": row["SJR"],
                            "rank": row["SJR Best Quartile"],
                            "issn": issn
                        })

            query = """
            UNWIND $journals AS row
            MERGE (j:Journal {issn: row.issn})
            SET j.title = row.title,
                j.sjr = row.sjr,
                j.rank = row.rank
            """
            with driver.session() as session:
                session.run(query, journals=journals)
        else:
            with open(self.file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    journal_data = row.get("journal", "")
                    publication = row.get("publicationVenue", "")
                    paper_id = row.get("paperId", "")

                    if not journal_data and not publication:
                        continue

                    try:
                        journal_info = {}
                        if journal_data:
                            if isinstance(journal_data, dict):
                                journal_info = journal_data
                            else:
                                journal_info = json.loads(journal_data.replace("'", '"'))

                        publication_info = {}
                        if publication:
                            if isinstance(publication, dict):
                                publication_info = publication
                            else:
                                publication_info = json.loads(publication.replace("'", '"'))

                        journal_node_id = None

                        if publication_info.get("issn"):
                            issn = publication_info.get("issn", "")
                            normalized_issn = issn.replace("-", "")
                            with driver.session() as session:
                                result = session.run("""
                                    MATCH (j:Journal {issn: $issn})
                                    RETURN id(j) as nodeId
                                """, issn=normalized_issn)
                                record = result.single()
                                if record:
                                    journal_node_id = record["nodeId"]

                        if journal_node_id is None and publication_info.get("alternate_issns"):
                            alternate_issns = publication_info.get("alternate_issns")
                            if isinstance(alternate_issns, str):
                                alternate_issns = json.loads(alternate_issns.replace("'", '"'))
                            for alt_issn in alternate_issns:
                                normalized_alt_issn = alt_issn.replace("-", "")
                                with driver.session() as session:
                                    result = session.run("""
                                        MATCH (j:Journal {issn: $issn})
                                        RETURN id(j) as nodeId
                                    """, issn=normalized_alt_issn)
                                    record = result.single()
                                    if record:
                                        journal_node_id = record["nodeId"]
                                        break

                        if journal_node_id is None:
                            journal_name = journal_info.get("name") or publication_info.get("name")
                            if journal_name:
                                with driver.session() as session:
                                    result = session.run("""
                                        MATCH (j:Journal {title: $name})
                                        RETURN id(j) as nodeId
                                    """, name=journal_name)
                                    record = result.single()
                                    if record:
                                        journal_node_id = record["nodeId"]

                        if journal_node_id is not None:
                            with driver.session() as session:
                                session.run("""
                                    MATCH (p:Paper {paperId: $paperId})
                                    MATCH (j:Journal) WHERE id(j) = $journalId
                                    MERGE (p)-[:IN_JOURNAL]->(j)
                                """, paperId=paper_id, journalId=journal_node_id)

                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in journal for paperId {paper_id}")