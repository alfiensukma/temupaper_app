import matplotlib.pyplot as plt
import pandas as pd
from neo4j import GraphDatabase
import logging
from itertools import product
import uuid
import os

# Konfigurasi logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Konfigurasi koneksi Neo4j
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")  # Ganti dengan URI Anda
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")        # Ganti dengan username Anda
PASSWORD = os.getenv("NEO4J_PASSWORD", "alfien0310")     # Ganti dengan password Anda

class Neo4jHandler:
    def __init__(self):
        self.driver = None
        self.graph_name = None
        try:
            self.driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
            self.driver.verify_connectivity()
            logger.info("Neo4jHandler berhasil diinisialisasi.")
        except Exception as e:
            logger.error(f"Gagal inisialisasi Neo4jHandler: {str(e)}")
            self.close()
            raise

    def create_search_node(self, query):
        try:
            paper_id = f"query-{uuid.uuid4()}"
            # Ganti dengan embedder asli Anda
            query_embedding = [0.1] * 384  # Dummy embedding, ganti dengan SentenceTransformerEmbeddings
            with self.driver.session() as session:
                session.run("""
                    CREATE (p:Paper {paperId: $paper_id})
                    SET p.title = $title,
                        p.search_embedding = $embedding
                """, paper_id=paper_id, title=query, embedding=query_embedding)
            logger.debug(f"Node pencarian dibuat: {paper_id}")
            return paper_id
        except Exception as e:
            logger.error(f"Error creating search node: {str(e)}")
            raise

    def delete_query_node(self, paper_id):
        try:
            with self.driver.session() as session:
                session.run("MATCH (p:Paper {paperId: $paperId}) DETACH DELETE p", paperId=paper_id)
                logger.debug(f"Node pencarian dihapus: {paper_id}")
        except Exception as e:
            logger.error(f"Error deleting query node '{paper_id}': {str(e)}")

    def create_graph_projection(self):
        try:
            self.graph_name = f"search_graph_{uuid.uuid4().hex}"
            logger.debug(f"Membuat graph projection: {self.graph_name}")
            with self.driver.session() as session:
                # Periksa apakah graph sudah ada dan hapus jika ada
                result = session.run("""
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
                logger.debug(f"Hasil pemeriksaan graph exists: {result.single()['value']}")
                
                # Buat graph projection
                session.run("""
                    CALL gds.graph.project($graph_name,
                        'Paper',
                        '*',
                        {
                            nodeProperties: ['search_embedding']
                        }
                    )
                """, graph_name=self.graph_name)
                logger.debug(f"Graph projection berhasil dibuat: {self.graph_name}")
            return self.graph_name
        except Exception as e:
            logger.error(f"Error creating graph projection: {str(e)}")
            self.drop_graph()
            raise

    def drop_graph(self):
        if not self.graph_name:
            logger.debug("Tidak ada graph untuk dihapus.")
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
                    logger.debug(f"Graph dihapus: {self.graph_name}")
        except Exception as e:
            logger.error(f"Error dropping graph '{self.graph_name}': {str(e)}")
        finally:
            self.graph_name = None

    def get_similarity_distribution(self, paper_id, top_k=10, similarity_threshold=0.0):
        if not self.graph_name:
            logger.error("Graph name tidak diatur. Panggil create_graph_projection terlebih dahulu.")
            raise ValueError("Graph name tidak diatur.")
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (p:Paper {paperId: $paperId})
                    CALL gds.knn.stream($graph_name, {
                        topK: $topK,
                        nodeProperties: ['search_embedding'],
                        concurrency: 2,
                        sampleRate: 1.0,
                        deltaThreshold: 0.1
                    })
                    YIELD node1, node2, similarity
                    WHERE 
                        gds.util.asNode(node1).paperId = $paperId
                        AND gds.util.asNode(node2).paperId <> $paperId
                        AND similarity > $similarityThreshold
                        AND NOT gds.util.asNode(node2).paperId STARTS WITH 'query-'
                    RETURN 
                        gds.util.asNode(node2).paperId AS paperId,
                        gds.util.asNode(node2).title AS title,
                        similarity
                    ORDER BY similarity DESC
                    LIMIT 1000
                """, paperId=paper_id, graph_name=self.graph_name, topK=top_k, 
                    similarityThreshold=similarity_threshold)
                similarities = [{'paperId': record['paperId'], 'title': record['title'], 
                                'similarity': record['similarity']} for record in result]
                logger.debug(f"Didapatkan {len(similarities)} hasil untuk paperId: {paper_id}, topK: {top_k}, threshold: {similarity_threshold}")
                return similarities
        except Exception as e:
            logger.error(f"Error fetching similarity distribution: {str(e)}")
            raise

    def close(self):
        if self.driver:
            self.driver.close()
            logger.debug("Koneksi Neo4j ditutup.")

def plot_histogram(similarities, query, top_k, similarity_threshold):
    df = pd.DataFrame(similarities, columns=['similarity'])
    
    plt.figure(figsize=(10, 6))
    plt.hist(df['similarity'], bins=50, color='skyblue', edgecolor='black')
    plt.title(f'Distribusi Similarity untuk Kueri: {query} (topK={top_k}, threshold={similarity_threshold})')
    plt.xlabel('Similarity (Cosine)')
    plt.ylabel('Frekuensi')
    plt.grid(True, alpha=0.3)
    
    stats = df['similarity'].describe()
    stats_text = f"Mean: {stats['mean']:.3f}\nMedian: {stats['50%']:.3f}\nStd: {stats['std']:.3f}"
    plt.text(0.05, 0.95, stats_text, transform=plt.gca().transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.savefig(f'similarity_histogram_{query}_topK{top_k}_threshold{similarity_threshold}.png', 
                dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\nStatistik Similarity untuk kueri '{query}' (topK={top_k}, threshold={similarity_threshold}):")
    print(stats)
    return stats

def evaluate_relevance(handler, paper_id, top_k, similarity_threshold, query):
    similarities = handler.get_similarity_distribution(paper_id, top_k, similarity_threshold)
    
    relevant_count = sum(1 for paper in similarities if query.lower() in paper['title'].lower())
    total_count = len(similarities)
    
    precision = relevant_count / total_count if total_count > 0 else 0.0
    recall = relevant_count / total_count if total_count > 0 else 0.0  # Proxy sederhana
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'topK': top_k,
        'similarity_threshold': similarity_threshold,
        'relevant_count': relevant_count,
        'total_count': total_count,
        'precision': precision,
        'f1_score': f1
    }

def main():
    handler = Neo4jHandler()
    try:
        queries = ["object oriented programming"]
        top_k_values = [1, 5, 10]
        similarity_thresholds = [0.5, 0.65, 0.8]
        
        results = []
        for query in queries:
            paper_id = handler.create_search_node(query)
            logger.debug(f"Memulai pengujian untuk kueri: {query}, paper_id: {paper_id}")
            
            try:
                handler.create_graph_projection()
                for top_k, sim_threshold in product(top_k_values, similarity_thresholds):
                    print(f"\nMenguji kueri: {query}, topK: {top_k}, similarity_threshold: {sim_threshold}")
                    
                    try:
                        similarities = handler.get_similarity_distribution(paper_id, top_k, sim_threshold)
                        
                        if similarities:
                            stats = plot_histogram([s['similarity'] for s in similarities], query, top_k, sim_threshold)
                            eval_result = evaluate_relevance(handler, paper_id, top_k, sim_threshold, query)
                            results.append({
                                'query': query,
                                **eval_result,
                                'mean_similarity': stats['mean'],
                                'median_similarity': stats['50%']
                            })
                        else:
                            print(f"Tidak ada data untuk kueri '{query}' dengan topK={top_k}, threshold={sim_threshold}")
                            results.append({
                                'query': query,
                                'topK': top_k,
                                'similarity_threshold': sim_threshold,
                                'relevant_count': 0,
                                'total_count': 0,
                                'precision': 0.0,
                                'f1_score': 0.0,
                                'mean_similarity': 0.0,
                                'median_similarity': 0.0
                            })
                    except Exception as e:
                        logger.error(f"Gagal menguji topK={top_k}, threshold={sim_threshold}: {str(e)}")
                        results.append({
                            'query': query,
                            'topK': top_k,
                            'similarity_threshold': sim_threshold,
                            'relevant_count': 0,
                            'total_count': 0,
                            'precision': 0.0,
                            'f1_score': 0.0,
                            'mean_similarity': 0.0,
                            'median_similarity': 0.0
                        })
                    finally:
                        handler.drop_graph()
            
            finally:
                handler.delete_query_node(paper_id)
        
        df_results = pd.DataFrame(results)
        print("\nHasil Evaluasi:")
        print(df_results)
        df_results.to_csv('knn_evaluation_results.csv', index=False)
        
        if not df_results.empty:
            best_params = df_results.loc[df_results['f1_score'].idxmax()]
            print("\nParameter Terbaik:")
            print(best_params)

    finally:
        handler.close()

if __name__ == "__main__":
    main()