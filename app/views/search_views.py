from django.shortcuts import render, redirect
from django.http import JsonResponse
from app.components.search_result import Neo4jHandler, PaperProcessor
from app.models import User
from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging

logger = logging.getLogger(__name__)

def index(request):
    topics = []
    user_id = request.session.get('user_id')
    access_history_papers = []
    peer_institution_papers = []
    neo4j_handler = Neo4jHandler()
    
    try:
        with neo4j_handler.driver.session() as session:
            # access history papers
            history_result = session.run("""
                MATCH (u:User {userId: $userId})-[:HAS_READ]->(n:Paper)-[r:HIGHEST_SIMILAR]->(p:Paper)
                WHERE NOT (u)-[:HAS_READ]->(p)
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    p.title AS title,
                    p.paperId as paperId,
                    p.abstract as abstract, 
                    p.publicationDate AS date,
                    p.year AS year,
                    p.pagerank as pagerank,
                    r.score as score,
                    collect(DISTINCT author.name) AS authors
                    ORDER BY r.score DESC, p.pagerank DESC, p.publicationDate DESC
                    LIMIT 5
                """,
                userId=user_id
            )
                
            for record in history_result:
                paper = dict(record)
                access_history_papers.append(paper)

            current_user = User.nodes.get(userId=user_id)
            institutionId = current_user.affiliated_with.all()[0].institutionId
            
            # peer institution papers
            peer_result = session.run("""
                MATCH (pt:Institution {institutionId: $institutionId})<-[:AFFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
                    WHERE NOT EXISTS {
                        MATCH (currentUser:User {userId: $userId})-[:HAS_READ]->(p)
                    }
                    WITH p, count(u) AS jumlahPembaca
                    OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                    RETURN 
                        p.title AS title,
                        p.paperId as paperId,
                        p.abstract as abstract, 
                        jumlahPembaca,
                        p.publicationDate AS date,
                        p.year AS year,
                        p.pagerank as pagerank,
                        collect(DISTINCT author.name) AS authors
                    ORDER BY jumlahPembaca DESC, p.pagerank DESC, p.publicationDate DESC, p.year DESC
                    LIMIT 5
                """, institutionId=institutionId, userId=user_id
            ) 
                
            for record in peer_result:
                paper = dict(record)
                peer_institution_papers.append(paper)
        
        with neo4j_handler.driver.session() as session:
            result = session.run("""
                MATCH (t:Topic)
                WITH t, rand() as r
                ORDER BY r
                LIMIT $limit
                RETURN t.name AS topic_name
            """, {
                'limit': 2
            })
            topics = [{"name": record["topic_name"]} for record in result]
    except Exception as e:
        print(f"Kesalahan mengambil topik untuk halaman utama: {str(e)}")
    finally:
        neo4j_handler.close()
    
    return render(request, "base.html", {
        "content_template": "search-paper/index.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False,
        "access_history_papers": access_history_papers,
        "peer_institution_papers": peer_institution_papers,
        "topics": topics
    })

def search(request):
    query = request.GET.get('query', '').strip()
    if not query:
        return redirect('index')

    request.session['last_search_query'] = query
    request.session[f"search_status_{query}"] = "pending"
    
    return render(request, "base.html", {
        "content_template": "search-paper/search-result.html",
        "body_class": "bg-gray-100",
        "show_search_form": True,
        "query": query
    })
    
def load_search_data(request):
    query = request.GET.get('query', '').strip()
    logger.info(f"Endpoint load_search_data dipanggil dengan query: '{query}'")
    if not query:
        return JsonResponse({'success': False, 'error': 'Silakan masukkan kueri pencarian.'})
    try:
        session_key = f"pure_search_{query}"
        if not request.session.get(session_key):
            logger.info(f"Melakukan pencarian baru untuk: '{query}'")
            neo4j_handler = Neo4jHandler()
            try:
                paper_id = neo4j_handler.create_search_node(query)
                neo4j_handler.create_graph_projection()
                seed_paper_ids = neo4j_handler.find_seed_papers(paper_id)
                if not seed_paper_ids:
                    return JsonResponse({'success': False, 'error': 'Tidak ditemukan hasil untuk kueri Anda.'})
                knn_details, similar_results = neo4j_handler.find_similar_papers(seed_paper_ids)
                papers = PaperProcessor.process_search_results(knn_details, similar_results)
                request.session[session_key] = papers
                request.session.modified = True
            finally:
                if paper_id:
                    neo4j_handler.delete_query_node(paper_id)
                neo4j_handler.close()
        else:
            logger.info(f"Menggunakan data cache dari session untuk query: '{query}'")
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error saat pencarian: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Terjadi kesalahan saat melakukan pencarian.'})