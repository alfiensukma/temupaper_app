from app.utils.neo4j_connection import get_neo4j_driver
import logging

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


def create_similar_paper_relation():
    try:
        driver = get_neo4j_driver()

        create_graph_projection(driver)

        with driver.session() as session:
            session.run(
                """
                MATCH (p1:Paper), (p2:Paper)
                WHERE p1.paper_id <> p2.paper_id AND p1.similarity_score > 0.8
                CREATE (p1)-[:SIMILAR_TO {similarity_score: p1.similarity_score}]->(p2)
                """
            )
            print("Similar paper relationships created successfully.")
    except Exception as e:
        print(f"Error connecting to Neo4j: {e}")
        return