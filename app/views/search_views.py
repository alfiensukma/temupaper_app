import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from app.components.search_result import Neo4jHandler, PaperProcessor
from neo4j.exceptions import ServiceUnavailable
from app.models import User
import logging
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

def index(request):
    topics = []
    user_id = request.session.get('user_id')
    access_history_papers = []
    peer_institution_papers = []
    handler = None
    
    try:
        handler = Neo4jHandler() 
        driver = handler.driver

        if not driver:
            raise Exception("Koneksi database Neo4j tidak berhasil diinisialisasi.")

        if user_id:
            with driver.session() as session:
                # history access
                history_result = session.run("""
                    MATCH (u:User {userId: $userId})-[:HAS_READ]->(:Paper)-[r:HIGHEST_SIMILAR]->(p:Paper)
                    WHERE NOT (u)-[:HAS_READ]->(p)
                    OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                    RETURN p.title AS title, p.paperId as paperId, p.abstract as abstract, 
                        p.publicationDate AS date, p.year AS year, p.pagerank as pagerank, 
                        r.score as score, collect(DISTINCT author.name) AS authors
                    ORDER BY r.score DESC, p.pagerank DESC, p.publicationDate DESC LIMIT 5
                """, userId=user_id)
                for record in history_result:
                    access_history_papers.append(dict(record))

                # peer institution
                current_user = User.nodes.get(userId=user_id)
                institution_node = current_user.affiliated_with.get_or_none()
                if institution_node:
                    institutionId = institution_node.institutionId
                    peer_result = session.run("""
                        MATCH (:Institution {institutionId: $institutionId})<-[:AFFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
                        WHERE NOT EXISTS { MATCH (:User {userId: $userId})-[:HAS_READ]->(p) }
                        WITH p, count(u) AS jumlahPembaca
                        OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                        RETURN p.title AS title, p.paperId as paperId, p.abstract as abstract, 
                            jumlahPembaca, p.publicationDate AS date, p.year AS year, 
                            p.pagerank as pagerank, collect(DISTINCT author.name) AS authors
                        ORDER BY jumlahPembaca DESC, p.pagerank DESC, p.publicationDate DESC, p.year DESC LIMIT 5
                    """, institutionId=institutionId, userId=user_id)
                    for record in peer_result:
                        peer_institution_papers.append(dict(record))
        else:
            logger.info("Pengunjung anonim, tidak mengambil rekomendasi personal.")

        # take topic
        with driver.session() as session:
            topic_result = session.run("""
                MATCH (t:Topic) WITH t, rand() as r
                ORDER BY r LIMIT 2
                RETURN t.name AS topic_name
            """)
            topics = [{"name": record["topic_name"]} for record in topic_result]
    
    except ServiceUnavailable as e:
        print(f"Kesalahan koneksi Neo4j: {str(e)}")        
    except Exception as e:
        print(f"Kesalahan mengambil data untuk halaman utama: {str(e)}")
        logger.error(f"Error di view index: {e}", exc_info=True)
    finally:
        if handler:
            handler.close()
    
    return render(request, "base.html", {
        "content_template": "search-paper/index.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False,
        "access_history_papers": access_history_papers,
        "peer_institution_papers": peer_institution_papers,
        "topics": topics
    })

def search(request):
    query = request.GET.get('query', request.session.get('last_search_query', '')).strip()
    if not query:
        return redirect('index')
    request.session['last_search_query'] = query
    request.session[f"search_status_{query}"] = "pending"
    logger.debug(f"Rendering search-result.html with query: '{query}'")
    
    handler = Neo4jHandler()
    try:
        paper_id = handler.create_search_node(query.lower())
        handler.create_graph_projection()
        seed_paper_ids = handler.find_seed_papers(paper_id)
        papers_data = []
        if seed_paper_ids:
            knn_details, similar_results = handler.find_similar_papers(seed_paper_ids)
            papers_data = PaperProcessor.process_search_results(knn_details, similar_results)
        request.session[f"pure_search_{query}"] = papers_data
        
        # pagination
        paginator = Paginator(papers_data, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "query": query,
            "years": range(2025, 2019, -1),
            "ranks": ["Q1", "Q2", "Q3", "Q4", "Tidak Teridentifikasi"],
            "pagination_data": paginator,
            "papers": page_obj.object_list
        })
    except Exception as e:
        logger.error(f"Error in search view: {str(e)}")
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "query": query,
            "years": range(2025, 2019, -1),
            "ranks": ["Q1", "Q2", "Q3", "Q4", "Tidak Teridentifikasi"],
            "error": f"Terjadi kesalahan: {str(e)}"
        })
    finally:
        if 'handler' in locals():
            if 'paper_id' in locals():
                handler.delete_query_node(paper_id)
            if hasattr(handler, 'graph_name') and handler.graph_name:
                handler.drop_graph()
            handler.close()

@csrf_protect
@require_GET
def search_api(request):
    logger.debug(f"search_api called with GET: {request.GET}")
    query = request.GET.get('query', '').strip()
    logger.debug(f"Query received: '{query}'")
    if not query:
        logger.warning("Empty query received in search_api")
        return JsonResponse({"error": "Kueri tidak boleh kosong"}, status=400)
    try:
        handler = Neo4jHandler()
        papers_data = []
        paper_id = handler.create_search_node(query.lower())
        handler.create_graph_projection()
        seed_paper_ids = handler.find_seed_papers(paper_id)
        if seed_paper_ids:
            knn_details, similar_results = handler.find_similar_papers(seed_paper_ids)
            papers_data = PaperProcessor.process_search_results(knn_details, similar_results)
        request.session[f"pure_search_{query}"] = papers_data
        return JsonResponse({"papers": papers_data}, safe=False)
    except Exception as e:
        logger.error(f"Error in search_api: {str(e)}")
        return JsonResponse({"error": f"Terjadi kesalahan: {str(e)}"}, status=500)
    finally:
        if 'handler' in locals():
            if 'paper_id' in locals():
                handler.delete_query_node(paper_id)
            if hasattr(handler, 'graph_name') and handler.graph_name:
                handler.drop_graph()
            handler.close()
            
@csrf_exempt
def test_search_process(request):
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Method tidak diizinkan. Gunakan POST.'
        }, status=405)

    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()

        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query pencarian tidak boleh kosong'
            }, status=400)

        logger.info(f"Testing search process for query: '{query}'")
        
        neo4j_handler = Neo4jHandler()
        try:
            # Step 1: Create search node
            paper_id = neo4j_handler.create_search_node(query)
            logger.info(f"Created search node with ID: {paper_id}")

            # Step 2: Create graph projection
            graph_name = neo4j_handler.create_graph_projection()
            logger.info(f"Created graph projection: {graph_name}")

            # Step 3: Find seed papers
            seed_paper_ids = neo4j_handler.find_seed_papers(paper_id)
            logger.info(f"Found {len(seed_paper_ids)} seed papers")

            # Step 4: Find similar papers
            if seed_paper_ids:
                knn_papers, similar_papers = neo4j_handler.find_similar_papers(seed_paper_ids)
                logger.info(f"Found {len(similar_papers)} similar papers")

                # Process the results
                processed_papers = []
                
                # Add KNN papers (seed papers details)
                for paper in knn_papers:
                    processed_papers.append({
                        'paperId': paper['paperId'],
                        'title': paper['title'],
                    })

                # Add similar papers
                for paper in similar_papers:
                    processed_papers.append({
                        'paperId': paper['paperId'],
                        'title': paper['title'],
                    })

                return JsonResponse({
                    'success': True,
                    'data': {
                        'query': query,
                        'search_node_id': paper_id,
                        'graph_name': graph_name,
                        'seed_papers': len(knn_papers),
                        'similar_papers': len(similar_papers),
                        'total_papers': len(processed_papers),
                        'papers': processed_papers
                    }
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No seed papers found for the given query'
                })

        finally:
            if paper_id:
                neo4j_handler.delete_query_node(paper_id)
            neo4j_handler.close()

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in test_search_process: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)