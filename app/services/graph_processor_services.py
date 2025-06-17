import logging
from app.utils.neo4j_connection import Neo4jConnection

logger = logging.getLogger(__name__)

class GraphPreprocessorService:
    def __init__(self):
        self.conn = Neo4jConnection()
        self.driver = self.conn.get_driver()

    def close(self):
        if self.conn:
            self.conn.close()

    def _project_embedding_graph(self, graph_name='myGraph'):
        with self.driver.session() as session:
            session.run(f"CALL gds.graph.drop('{graph_name}', false)")
            
            result = session.run("""
                CALL gds.graph.project(
                    $graph_name,
                    'Paper',
                    {
                        nodeProperties: 'search_embedding'
                    }
                ) YIELD graphName
                RETURN graphName
            """, graph_name=graph_name)
            
            logger.info(f"Graph projection '{result.single()['graphName']}' berhasil dibuat untuk embedding.")

    def run_similarity_calculations(self, graph_name='myGraph'):
        self._project_embedding_graph(graph_name)
        
        with self.driver.session() as session:
            session.run("MATCH ()-[r:HIGHEST_SIMILAR]->() DELETE r")
            session.run("MATCH ()-[r:SIMILAR]->() DELETE r")
            logger.info("Relasi similarity lama telah dihapus.")

            session.run("""
                CALL gds.knn.write($graph_name, {
                    writeRelationshipType: 'HIGHEST_SIMILAR',
                    writeProperty: 'score',
                    topK: 1,
                    nodeProperties: ['search_embedding']
                }) YIELD relationshipsWritten
            """, graph_name=graph_name)
            logger.info("Relasi HIGHEST_SIMILAR berhasil dibuat.")

            session.run("""
                CALL gds.knn.write($graph_name, {
                    writeRelationshipType: 'SIMILAR',
                    writeProperty: 'score',
                    topK: 50,
                    nodeProperties: ['search_embedding']
                }) YIELD relationshipsWritten
            """, graph_name=graph_name)
            logger.info("Relasi SIMILAR berhasil dibuat.")
            session.run(f"CALL gds.graph.drop('{graph_name}')")

    def run_pagerank_calculation(self, graph_name='pageGraph'):
        with self.driver.session() as session:
            session.run(f"CALL gds.graph.drop('{graph_name}', false)")
            
            session.run("""
                CALL gds.graph.project(
                    $graph_name,
                    'Paper',
                    'REFERENCES'
                )
            """, graph_name=graph_name)
            logger.info(f"Graph projection '{graph_name}' berhasil dibuat untuk PageRank.")
            
            session.run("""
                CALL gds.pageRank.write($graph_name, {
                    maxIterations: 20,
                    dampingFactor: 0.85,
                    writeProperty: 'pagerank'
                }) YIELD nodePropertiesWritten
            """, graph_name=graph_name)
            logger.info("Kalkulasi PageRank berhasil dan telah ditulis ke node.")

            session.run(f"CALL gds.graph.drop('{graph_name}')")