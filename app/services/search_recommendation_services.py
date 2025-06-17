from django.apps import apps
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import logging
import uuid
import os
from django.apps import apps

logger = logging.getLogger(__name__)

class Neo4jHandler:
    def __init__(self):
        self.driver = None
        self._embedder = None
        self.graph_name = None

        try:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USERNAME", "neo4j")
            password = os.getenv("NEO4J_PASSWORD")
            if not password:
                raise ValueError("Password Neo4j (NEO4J_PASSWORD) tidak ditemukan.")
            
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            self._embedder = apps.get_app_config('app').embedder
            if not self._embedder:
                raise Exception("Global embedder tidak berhasil dimuat dari AppConfig.")

            logger.info("Neo4jHandler berhasil diinisialisasi.")

        except (ServiceUnavailable, ValueError, Exception) as e:
            logger.error(f"Gagal saat inisialisasi Neo4jHandler: {e}")
            self.close()
            raise
        
    def get_driver(self):
        return self.driver

    @property
    def embedder(self):
        if self._embedder is None:
            preloaded_model = apps.get_app_config('app').embedder_model
            if not preloaded_model:
                raise Exception("Embedding model tidak tersedia.")
            self._embedder = SentenceTransformerEmbeddings(model=preloaded_model)
        return self._embedder

    def create_search_node(self, query):
        try:
            paper_id = f"query-{uuid.uuid4()}"
            query_embedding = self.embedder.embed_query(query)
            if hasattr(query_embedding, 'tolist'):
                query_embedding = query_embedding.tolist()
            
            with self.driver.session() as session:
                session.run("""
                    CREATE (p:Paper {paperId: $paper_id})
                    SET p.title = $title,
                        p.search_embedding = $embedding
                """, paper_id=paper_id, title=query, embedding=query_embedding)
            
            return paper_id
        except Exception as e:
            logger.error(f"Error creating search node: {str(e)}")
            raise Exception(f"Gagal membuat node pencarian: {str(e)}")

    def delete_query_node(self, paper_id):
        try:
            with self.driver.session() as session:
                session.run("MATCH (p:Paper {paperId: $paperId}) DETACH DELETE p", paperId=paper_id)
        except Exception as e:
            logger.error(f"Error deleting query node '{paper_id}': {str(e)}")

    def create_graph_projection(self):
        try:
            self.graph_name = f"search_graph_{uuid.uuid4().hex}"
            with self.driver.session() as session:
                session.run("""
                    CALL gds.graph.exists($graph_name) YIELD exists
                    WITH exists
                    CALL apoc.do.when(
                        exists,
                        'CALL gds.graph.drop($graph_name) YIELD graphName RETURN graphName',
                        'RETURN null as graphName',
                        {graph_name: $graph_name}
                    ) YIELD value
                    RETURN value
                """, graph_name=self.graph_name)
                
                session.run("""
                    CALL gds.graph.project($graph_name,
                        'Paper',
                        '*',
                        {
                            nodeProperties: ['search_embedding']
                        }
                    )
                """, graph_name=self.graph_name)
            return self.graph_name
        except Exception as e:
            logger.error(f"Error creating graph projection: {str(e)}")
            if self.graph_name:
                self.drop_graph()
            raise Exception(f"Gagal membuat proyeksi graf: {str(e)}")

    def drop_graph(self):
        if not self.graph_name:
            return
        try:
            with self.driver.session() as session:
                exists = session.run(
                    "CALL gds.graph.exists($name) YIELD exists",
                    name=self.graph_name
                ).single()["exists"]
                if exists:
                    session.run(
                        "CALL gds.graph.drop($name) YIELD graphName",
                        name=self.graph_name
                    )
        except Exception as e:
            logger.error(f"Error dropping graph '{self.graph_name}': {str(e)}")
        finally:
            self.graph_name = None

    def find_seed_papers(self, paper_id):
        if not self.graph_name:
            raise Exception("Graph name not set. Create graph projection first.")
        try:
            with self.driver.session() as session:
                knn_results = session.run("""
                    MATCH (p:Paper {paperId: $paperId})
                    CALL gds.knn.stream($graph_name, {
                        topK: 10,
                        nodeProperties: ['search_embedding'],
                        concurrency: 4,
                        sampleRate: 1.0,
                        deltaThreshold: 0.1
                    })
                    YIELD node1, node2, similarity
                    WHERE 
                        gds.util.asNode(node1).paperId = $paperId
                        AND gds.util.asNode(node2).paperId <> $paperId
                        AND similarity > 0.7
                        AND NOT gds.util.asNode(node2).paperId STARTS WITH 'query-'
                    RETURN 
                        gds.util.asNode(node2).paperId AS paperId,
                        similarity,
                        gds.util.asNode(node2).title as title
                    ORDER BY similarity DESC
                    LIMIT 1
                """, paperId=paper_id, graph_name=self.graph_name)
                seed_papers = [record["paperId"] for record in knn_results]
                return seed_papers
        except Exception as e:
            logger.error(f"Error finding seed papers: {str(e)}")
            raise

    def find_similar_papers(self, seed_paper_ids):
        if not seed_paper_ids:
            return [], []
        try:
            with self.driver.session() as session:
                knn_details = session.run("""
                    UNWIND $paperIds AS knnPaperId
                    MATCH (paper:Paper {paperId: knnPaperId})
                    OPTIONAL MATCH (paper)-[:AUTHORED_BY]->(author:Author)
                    OPTIONAL MATCH (paper)-[:IN_JOURNAL]->(journal:Journal)
                    RETURN 
                        paper.paperId AS paperId,
                        paper.title AS title, 
                        paper.abstract AS abstract,
                        paper.publicationDate AS date,
                        paper.year AS year,
                        paper.citationCount AS citation_count,
                        1.0 AS similarity_score,
                        collect(DISTINCT author.name) AS authors, 
                        COALESCE(journal.rank, '') AS rank
                """, paperIds=seed_paper_ids)
                knn_records = list(knn_details)
                
                similar_results = session.run("""
                    UNWIND $paperIds AS topPaperId
                    MATCH (top:Paper {paperId: topPaperId})
                    OPTIONAL MATCH (top)-[r:SIMILAR]->(paper:Paper)
                    OPTIONAL MATCH (paper)-[:AUTHORED_BY]->(author:Author)
                    OPTIONAL MATCH (paper)-[:IN_JOURNAL]->(journal:Journal)
                    RETURN 
                        paper.paperId AS paperId,
                        paper.title AS title, 
                        paper.abstract AS abstract,
                        paper.publicationDate AS date,
                        paper.year AS year,
                        paper.citationCount AS citation_count,
                        paper.pageRank AS pageRank,
                        r.score AS similarity_score,
                        collect(DISTINCT author.name) AS authors,
                        COALESCE(journal.rank, '') AS rank
                    ORDER BY similarity_score DESC, pageRank DESC
                    LIMIT 49
                """, paperIds=seed_paper_ids)
                similar_records = list(similar_results)
                
                return knn_records, similar_records
        except Exception as e:
            logger.error(f"Error finding similar papers: {str(e)}")
            raise
        finally:
            self.drop_graph()

    def close(self):
        if self.driver:
            self.driver.close()