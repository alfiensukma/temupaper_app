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
            topic_count = session.run("MATCH (t:Topic) RETURN count(t) AS count").single()["count"]

        return {
            "total_papers": paper_count,
            "total_authors": author_count,
            "total_publication_type": publication_type_count,
            "total_fields_of_study": field_of_study_count,
            "journal_count": journal_count,
            "institution_count": institution_count,
            "topic_count": topic_count,
        }
        
    def get_count(self, label):
        with self.connection.get_driver().session() as session:
            result = session.run(f"MATCH (n:{label}) RETURN COUNT(n) as count")
            return result.single()["count"] if result.peek() else 0

    def import_all(self, import_configs):
        # self.clear_graph()
        importers = []
        total_steps = len(import_configs)
        current_step = 0
        
        try:
            for config in import_configs:
                current_step += 1
                importer_type = config["type"]
                file_path = config["file_path"]
                
                self.logger.info(f"[{current_step}/{total_steps}] Importing {importer_type}")
                self.logger.debug(f"Reading file: {file_path}")
            
                with open(file_path, 'r', encoding='utf-8') as f:
                    header = f.readline().strip()
                    first_line = f.readline().strip()
                    self.logger.debug(f"CSV Header: {header}")
                    self.logger.debug(f"First line: {first_line}")
                
                kwargs = config.get("kwargs", {})
                importer = ImporterFactory.create_importer(importer_type, file_path, **kwargs)
                importers.append(importer)
                
                try:
                    importer.import_data(self.connection.get_driver())
                    self.logger.info(f"Successfully imported {importer_type}")
                except Exception as e:
                    self.logger.error(f"Error importing {importer_type}: {str(e)}")
                    raise
                
                self.logger.info(f"Finished importing {importer_type}")

            validation_result = self.validate_graph()
            self.logger.info("Knowledge graph validation completed")
            return validation_result

        except Exception as e:
            self.logger.error(f"Error during import: {str(e)}")
            raise Exception(f"Import failed: {str(e)}. Current step: {current_step}/{total_steps}, Type: {importer_type}")

    def close_connection(self):
        self.connection.close()