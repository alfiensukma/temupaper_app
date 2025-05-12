import logging
from app.importers.importer_factory import ImporterFactory

class KnowledgeGraphManager:
    def __init__(self, neo4j_connection):
        self.connection = neo4j_connection
        self.logger = logging.getLogger(__name__)

    def clear_graph(self):
        with self.connection.get_driver().session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def validate_graph(self):
        with self.connection.get_driver().session() as session:
            paper_count = session.run("MATCH (p:Paper) RETURN count(p) AS count").single()["count"]
            author_count = session.run("MATCH (a:Author) RETURN count(a) AS count").single()["count"]
            publication_type_count = session.run("MATCH (pt:PublicationType) RETURN count(pt) AS count").single()["count"]
            field_of_study_count = session.run("MATCH (f:FieldOfStudy) RETURN count(f) AS count").single()["count"]
            journal_count = session.run("MATCH (j:Journal) RETURN count(j) AS count").single()["count"]
            institution_count = session.run("MATCH (i:Institution) RETURN count(i) AS count").single()["count"]

        return {
            "total_papers": paper_count,
            "total_authors": author_count,
            "total_publication_type": publication_type_count,
            "total_fields_of_study": field_of_study_count,
            "journal_count": journal_count,
            "institution_count": institution_count
        }

    def import_all(self, import_configs):
        self.clear_graph()
        importers = []
        for config in import_configs:
            importer_type = config["type"]
            file_path = config["file_path"]
            kwargs = config.get("kwargs", {})
            importer = ImporterFactory.create_importer(importer_type, file_path, **kwargs)
            importers.append(importer)

        for importer in importers:
            self.logger.info(f"Importing data from {importer.file_path}")
            importer.import_data(self.connection.get_driver())

        validation_result = self.validate_graph()
        self.logger.info("Knowledge graph validation completed")
        return validation_result, importers

    def close_connection(self):
        self.connection.close()