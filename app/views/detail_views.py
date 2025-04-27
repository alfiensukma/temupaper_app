from django.shortcuts import render, redirect
from django.http import JsonResponse
from app.utils.neo4j_connection import get_neo4j_driver
from dotenv import load_dotenv
import logging
from datetime import datetime
import ast


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def get_recommendation(request):
    paperId = request.GET.get('paper_id')
    if not paperId:
        return JsonResponse({'error': 'Missing paperId'}, status=400)

    driver = None
    try:
        driver = get_neo4j_driver()

        # Check if the graph exists, if so, drop it
        with driver.session() as session:
            graph_exists = session.run("""
                CALL gds.graph.exists('detailGraph')
                YIELD exists
                RETURN exists
            """).single()["exists"]

        if graph_exists:
            with driver.session() as session:
                session.run("""
                    CALL gds.graph.drop('detailGraph', false)
                    YIELD graphName
                    RETURN graphName
                """)
                print("Existing 'detailGraph' dropped.")

        # Create the graph projection with only nodes having embeddings
        with driver.session() as session:
            session.run("""
                CALL gds.graph.project.cypher(
                    'detailGraph',
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
                CALL gds.knn.stream('detailGraph', {
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

def get_detail_json(request):
    paperId = request.GET.get('paper_id')
    if not paperId:
        return JsonResponse({'error': 'Missing paper_id'}, status=400)

    driver = None
    try:
        driver = get_neo4j_driver()

        with driver.session() as session:
            result = session.run("""
                MATCH (p:Paper {paperId: $paperId})
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                RETURN p.title as title, 
                    p.abstract as abstract,
                    p.publicationDate as pubDate,
                    p.doi as doi,
                    p.url as url,
                    collect({name: a.name, id: a.authorId}) as authors
            """, paperId=paperId)
            
            # Ambil hasil dari query
            record = result.single()
            
            # Cek apakah paper ditemukan
            if not record:
                return JsonResponse({'error': 'Paper not found'}, status=404)
                
            # Parsing data dari record
            data = {
                "title": record["title"],
                "abstract": record["abstract"],
                "pubDate": record["pubDate"],
                "doi": record["doi"],
                "url": record["url"],
                "authors": record["authors"]
            }

        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if driver:
            driver.close()

def get_paper_detail(request, paper_id):
    try:
        # Get Neo4j driver
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            # Get paper details
            result = session.run("""
                MATCH (p:Paper {paperId: $paperId})
                RETURN p.paperId AS paperId,
                       p.title AS title,
                       p.abstract AS abstract,
                       p.authors AS authors,
                       p.publicationDate AS date,
                       p.externalIds AS externalIds,
                       p.url AS url,
                       p.cso_topics AS topics
            """, paperId=paper_id).single()

            if not result:
                raise Exception("Paper not found")
            
            external_ids = {}
            if result["externalIds"]:
                try:
                    external_ids = ast.literal_eval(result["externalIds"])
                except:
                    external_ids = {}

            paper = {
                "id": result["paperId"],
                "title": result["title"],
                "abstract": result["abstract"] or "",
                "authors": result["authors"] or [],
                "date": result["date"] or "",
                "doi": external_ids.get('DOI', ''),
                "url": result["url"] or "",
            }

            # Format date if exists
            if paper["date"]:
                dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                paper["date"] = dt.strftime("%d %B %Y")

            # Dummy related papers for carousel
            paper_recommendation = [
                {
                    "id": "1",
                    "title": "Understanding Deep Learning Requires Rethinking Generalization",
                    "abstract": "Deep learning has achieved remarkable success in many applications...",
                    "authors": ["Zhang, Chiyuan", "Bengio, Samy", "Hardt, Moritz"],
                    "date": "15 March 2024"
                },
                {
                    "id": "2", 
                    "title": "Attention Is All You Need",
                    "abstract": "The dominant sequence transduction models are based on complex recurrent neural networks...",
                    "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
                    "date": "12 March 2024"
                },
                {
                    "id": "3",
                    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                    "abstract": "We introduce a new language representation model called BERT...",
                    "authors": ["Devlin, Jacob", "Chang, Ming-Wei"],
                    "date": "10 March 2024"
                }
            ]

        driver.close()

        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "paper": paper,
            "paper_recommendation": paper_recommendation
        })

    except Exception as e:
        logger.error(f"Error getting paper detail: {str(e)}")
        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"An error occurred: {str(e)}"
        })