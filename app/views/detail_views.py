from django.shortcuts import render, redirect
from django.http import JsonResponse
from app.utils.neo4j_connection import get_neo4j_driver
from dotenv import load_dotenv
import logging
from datetime import datetime
import ast
from app.models import User, Paper


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

def get_recommendation(paper_id):
    if not paper_id:
        return JsonResponse({'error': 'Missing paperId'}, status=400)

    driver = None
    try:
        driver = get_neo4j_driver()

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

        with driver.session() as session:
            session.run("""
                MATCH (p:Paper)
                RETURN gds.graph.project(
                    'detailGraph',
                    p,
                    null,
                    {
                        sourceNodeProperties: p { .embedding },
                        targetNodeProperties: {}
                    }
                )
            """)
            print("Graph 'detailGraph' created, excluding papers without embeddings.")

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
                WITH gds.util.asNode(node2) AS recommendedPaper, similarity
                OPTIONAL MATCH (recommendedPaper)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    recommendedPaper.paperId AS paperId,
                    recommendedPaper.title AS title, 
                    recommendedPaper.publicationDate AS date,
                    recommendedPaper.abstract AS abstract,
                    recommendedPaper.year AS year,
                    similarity,
                    collect({name: author.name, id: author.authorId}) AS authors
                ORDER BY similarity DESC
            """, paperId=paper_id)

            data = [{
                "paperId": record["paperId"],
                "title": record["title"],
                "date": record["date"],
                "similarity": record["similarity"],
                "abstract": record["abstract"],
                "authors": record["authors"],
                "year": record["year"]
            } for record in result]

            for paper in data:
                if paper["date"]:
                    try:
                        try:
                            dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            dt = datetime.strptime(paper["date"], "%Y-%m-%d")
                        paper["date"] = dt.strftime("%d %B %Y")
                    except Exception as e:
                        logger.error(f"Date parse error for paper {paper['paperId']}: {e}")
                        paper["date"] = paper.get("year", "Unknown date")
                else:
                    paper["date"] = paper.get("year", "Unknown date")
                    
        return data

    except Exception as e:
        print(f"Error in get_recommendation: {str(e)}")
        return []
    finally:
        if driver:
            driver.close()

def get_detail_json(request, paper_id):
    if not paper_id:
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
                    p.publicationDate as date,
                    p.year as year,
                    p.doi as doi,
                    p.url as url,
                    collect({name: a.name, id: a.authorId}) as authors
            """, paperId=paper_id)

            record = result.single()

            if not record:
                return JsonResponse({'error': 'Paper not found'}, status=404)

            paper = {
                "paperId": paper_id,
                "title": record["title"],
                "abstract": record["abstract"],
                "date": record["date"],
                "doi": record["doi"],
                "url": record["url"],
                "year": record["year"],
                "authors": record["authors"]
            }

            if paper["date"]:
                try:
                    try:
                        dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        dt = datetime.strptime(paper["date"], "%Y-%m-%d")
                    paper["date"] = dt.strftime("%d %B %Y")
                except Exception as e:
                    logger.error(f"Date parse error for paper {paper['paperId']}: {e}")
                    paper["date"] = paper.get("year", "Unknown date")
            else:
                paper["date"] = paper.get("year", "Unknown date")
        
        driver.close()

        paper_recommendation = get_recommendation(paper_id)

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

def get_paper_detail(request, paper_id):
    try:
        driver = get_neo4j_driver()
        
        with driver.session() as session:
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

            if paper["date"]:
                dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                paper["date"] = dt.strftime("%d %B %Y")

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
    
def record_paper_read(request):
    if request.method == 'POST':
        paper_id = request.POST.get('paper_id')
        access_method = request.POST.get('access_method')

        user_id = request.session.get('user_id', '')
        
        logger.info(f"Recording paper read - User ID: {user_id}, Paper ID: {paper_id}, Access Method: {access_method}")
        
        if not user_id:
            return JsonResponse({'status': 'error', 'message': 'User not authenticated'}, status=401)
        
        try:
            user = User.nodes.get(userId=user_id)
            paper = Paper.nodes.get(paperId=paper_id)

            existing_relations = list(user.has_read.all_relationships(paper))
            
            if existing_relations:
                rel = existing_relations[0]
                rel.read_at = datetime.now()
                rel.access_method = access_method
                rel.save()
                logger.info(f"Updated existing read relationship")
            else:
                user.has_read.connect(paper, {
                    'read_at': datetime.now(),
                    'access_method': access_method
                })
                logger.info(f"Created new read relationship")
            
            return JsonResponse({'status': 'success', 'message': 'Paper read recorded'})
        
        except User.DoesNotExist:
            logger.error(f"User not found with ID: {user_id}")
            return JsonResponse({'status': 'error', 'message': f'User not found with ID: {user_id}'}, status=404)
        except Paper.DoesNotExist:
            logger.error(f"Paper not found with ID: {paper_id}")
            return JsonResponse({'status': 'error', 'message': f'Paper not found with ID: {paper_id}'}, status=404)
        except Exception as e:
            logger.error(f"Error recording paper read: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)