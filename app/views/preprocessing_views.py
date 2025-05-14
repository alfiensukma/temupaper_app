from app.utils.neo4j_connection import Neo4jConnection
import logging
from django.http import HttpResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_graph_projection(driver):
    with driver.session() as session:
        try:
            # Cek dulu apakah graph sudah ada
            check_result = session.run("CALL gds.graph.exists('myGraph') YIELD exists RETURN exists")
            if check_result.single()["exists"]:
                logger.info("Graph 'myGraph' already exists. Dropping it first...")
                session.run("CALL gds.graph.drop('myGraph')")
            
            # Buat graph projection baru
            result = session.run("""
                MATCH (p:Paper) WHERE p.embedding IS NOT NULL
                RETURN gds.graph.project(
                    'myGraph',
                    p,
                    null,
                    {
                        sourceNodeProperties: p { .embedding },
                        targetNodeProperties: {}
                    }
                )
            """)

            if result:
                logger.info("Graph projection created successfully")
                return True
            else: 
                logger.error("Failed to create graph projection")
                return False
        except Exception as e:
            logger.error(f"Error creating graph: {e}")
            return False


def create_similar_paper_relation(request):
    try:
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()

        if not create_graph_projection(driver):
            logger.error("Failed to create graph projection. Aborting...")
            return HttpResponse("Failed to create graph projection.", status=500)

        with driver.session() as session:
            # Hapus relasi HIGHEST_SIMILAR yang sudah ada
            session.run("MATCH ()-[r:HIGHEST_SIMILAR]->() DELETE r")
            logger.info("Existing HIGHEST_SIMILAR relationships deleted.")

            # Buat relasi HIGHEST_SIMILAR baru (topK = 1)
            session.run(
                """
                CALL gds.knn.write('myGraph', {
                    writeRelationshipType: 'HIGHEST_SIMILAR',
                    writeProperty: 'score',
                    topK: 1,
                    randomSeed: 42,
                    concurrency: 1,
                    nodeProperties: ['embedding']
                })
                YIELD nodesCompared, relationshipsWritten
                """
            )
            logger.info("Highest similarity relationship created successfully.")

            # Hapus relasi SIMILAR yang sudah ada
            session.run("MATCH ()-[r:SIMILAR]->() DELETE r")
            logger.info("Existing SIMILAR relationships deleted.")

            # Buat relasi SIMILAR baru (topK = 10)
            session.run(
                """
                CALL gds.knn.write('myGraph', {
                    writeRelationshipType: 'SIMILAR',
                    writeProperty: 'score',
                    topK: 50,
                    randomSeed: 42,
                    concurrency: 1,
                    nodeProperties: ['embedding']
                })
                YIELD nodesCompared, relationshipsWritten
                """
            )
            logger.info("Similar paper relationships created successfully.")
        
        return HttpResponse("Relationships created successfully.", status=200)
    except Exception as e:
        logger.exception("Error connecting to Neo4j")
        return HttpResponse(f"Error: {e}", status=500)
    finally:
        if 'driver' in locals() and driver:
            driver.close()

def create_graph_projection_page(driver):
    with driver.session() as session:
        try:
            # Cek dulu apakah graph sudah ada
            check_result = session.run("CALL gds.graph.exists('pageGraph') YIELD exists RETURN exists")
            if check_result.single()["exists"]:
                logger.info("Graph 'myGraph' already exists. Dropping it first...")
                session.run("CALL gds.graph.drop('pageGraph')")
            
            # Buat graph projection baru
            result = session.run("""
                MATCH (source:Paper)-[r:REFERENCES]->(target:Paper)
                RETURN gds.graph.project(
                    'pageGraph',
                    source,
                    target
                )
            """)

            if result:
                logger.info("Graph projection created successfully")
                return True
            else: 
                logger.error("Failed to create graph projection")
                return False
        except Exception as e:
            logger.error(f"Error creating graph: {e}")
            return False


def create_page_rank(request):
    try:
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()

        if not create_graph_projection_page(driver):
            logger.error("Failed to create graph projection. Aborting...")
            return HttpResponse("Failed to create graph projection.", status=500)

        with driver.session() as session:
            # Buat relasi HIGHEST_SIMILAR baru (topK = 1)
            session.run(
                """
                CALL gds.pageRank.write('pageGraph', {
                    maxIterations: 20,
                    dampingFactor: 0.85,
                    writeProperty: 'pagerank'
                })
                YIELD nodePropertiesWritten, ranIterations
                """
            )
            logger.info("PageRank calculated successfully.")
        
        return HttpResponse("PageRank calculated successfully.", status=200)
    except Exception as e:
        logger.exception("Error connecting to Neo4j")
        return HttpResponse(f"Error: {e}", status=500)
    finally:
        if 'driver' in locals() and driver:
            driver.close()