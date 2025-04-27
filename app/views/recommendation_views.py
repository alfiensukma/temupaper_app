from django.http import JsonResponse
from langchain_community.graphs import Neo4jGraph
import os
from dotenv import load_dotenv

load_dotenv()

def get_neo4j_graph():
    return Neo4jGraph(
        url=os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
        username=os.getenv('NEO4J_USERNAME', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD')
    )

def get_all_paper_titles(request):
    paperId = request.GET.get('paper_id')
    if not paperId:
        return JsonResponse({'error': 'Missing paperId'}, status=400)

    try:
        graph = get_neo4j_graph()

        # Check if the graph exists, if so, drop it
        graph_exists = graph.query("""
            CALL gds.graph.exists('paperGraph')
            YIELD exists
            RETURN exists
        """)[0]["exists"]

        if graph_exists:
            graph.query("""
                CALL gds.graph.drop('paperGraph', false)
                YIELD graphName
                RETURN graphName
            """)
            print("Existing 'paperGraph' dropped.")

        # Create the graph projection with only nodes having embeddings
        graph.query("""
            CALL gds.graph.project.cypher(
                'paperGraph',
                'MATCH (p:Paper) WHERE p.embedding IS NOT NULL RETURN id(p) AS id, p.embedding AS embedding',
                'RETURN null AS source, null AS target LIMIT 0',
                { readConcurrency: 4 }
            )
        """)
        print("Graph 'paperGraph' created, excluding papers without embeddings.")

        # Run the KNN query
        result = graph.query("""
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
        """, params={"paperId": paperId})

        data = [{"title": row["title"], "similarity": row["similarity"]} for row in result]
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)