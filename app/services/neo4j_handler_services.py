from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
import logging
import uuid

logger = logging.getLogger(__name__)
embedder = SentenceTransformerEmbeddings(model="all-mpnet-base-v2")

class Neo4jHandler:
    def __init__(self):
        from app.utils.neo4j_connection import Neo4jConnection
        self.connection = Neo4jConnection()
        self.driver = self.connection.get_driver()
        self.graph_name = None

    def create_search_node(self, query):
        try:
            paper_id = f"query-{uuid.uuid4()}"
            query_embedding = embedder.embed_query(query)
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
                    WHERE gds.util.asNode(node1).paperId = $paperId
                    RETURN gds.util.asNode(node2).paperId AS paperId, similarity
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
                    RETURN 
                        paper.paperId AS paperId,
                        paper.title AS title, 
                        paper.abstract AS abstract,
                        paper.publicationDate AS date,
                        paper.year AS year,
                        paper.citationCount AS citation_count,
                        1.0 AS similarity_score,
                        collect(DISTINCT author.name) AS authors
                """, paperIds=seed_paper_ids)
                knn_records = list(knn_details)
                
                similar_results = session.run("""
                    UNWIND $paperIds AS topPaperId
                    MATCH (top:Paper {paperId: topPaperId})
                    OPTIONAL MATCH (top)-[r:SIMILAR]->(paper:Paper)
                    OPTIONAL MATCH (paper)-[:AUTHORED_BY]->(author:Author)
                    RETURN 
                        paper.paperId AS paperId,
                        paper.title AS title, 
                        paper.abstract AS abstract,
                        paper.publicationDate AS date,
                        paper.year AS year,
                        paper.citationCount AS citation_count,
                        paper.pageRank AS pageRank,
                        r.score AS similarity_score,
                        collect(DISTINCT author.name) AS authors
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
        try:
            self.drop_graph()
        finally:
            if self.driver:
                self.driver.close()