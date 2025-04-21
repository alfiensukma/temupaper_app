from django.http import JsonResponse
from app.utils.neo4j_connection import get_neo4j_driver
from dotenv import load_dotenv

load_dotenv()

def get_all_paper_titles(request):
    paperId = request.GET.get('paper_id')
    if not paperId:
        return JsonResponse({'error': 'Missing paperId'}, status=400)

    driver = None
    try:
        driver = get_neo4j_driver()

        # Check if the graph exists, if so, drop it
        with driver.session() as session:
            graph_exists = session.run("""
                CALL gds.graph.exists('paperGraph')
                YIELD exists
                RETURN exists
            """).single()["exists"]

        if graph_exists:
            with driver.session() as session:
                session.run("""
                    CALL gds.graph.drop('paperGraph', false)
                    YIELD graphName
                    RETURN graphName
                """)
                print("Existing 'paperGraph' dropped.")

        # Create the graph projection with only nodes having embeddings
        with driver.session() as session:
            session.run("""
                CALL gds.graph.project.cypher(
                    'paperGraph',
                    'MATCH (p:Paper) WHERE p.embedding IS NOT NULL RETURN id(p) AS id, p.embedding AS embedding',
                    'RETURN null AS source, null AS target LIMIT 0',
                    { readConcurrency: 4 }
                )
            """)
            print("Graph 'paperGraph' created, excluding papers without embeddings.")

        # Run the KNN query
        with driver.session() as session:
            result = session.run("""
                MATCH (p:Paper {paperId: $paperId})
                WITH id(p) AS targetId
                CALL gds.knn.stream('paperGraph', {
                    topK: 5,
                    nodeProperties: ['embedding'],
                    randomSeed: 42,
                    concurrency: 1,
                    sampleRate: 1.0,
                    deltaThreshold: 0.0
                })
                YIELD node1, node2, similarity
                WHERE node1 = targetId
                RETURN gds.util.asNode(node2).title AS title, similarity
                ORDER BY similarity DESC
            """, paperId=paperId)
            data = [{"title": record["title"], "similarity": record["similarity"]} for record in result]

        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if driver:
            driver.close()