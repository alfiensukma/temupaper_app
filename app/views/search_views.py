import json
import time
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_GET
from app.services.search_recommendation_services import Neo4jHandler
from neo4j.exceptions import ServiceUnavailable
from app.models import User
import logging

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

def clear_old_sessions(request, current_query):
    last_query = request.session.get('last_search_query', '')
    if last_query and last_query != current_query:
        session_keys = [key for key in request.session.keys() if key.startswith('pure_search_') or key.startswith('search_status_')]
        for key in session_keys:
            logger.debug(f"Menghapus sesi lama: {key}")
            del request.session[key]
        request.session.modified = True
        request.session.save()

def get_papers(request):
    query = request.GET.get('query', '').strip()
    if not query:
        return HttpResponseRedirect('index')
    
    clear_old_sessions(request, query)
    
    request.session['last_search_query'] = query
    request.session[f"search_status_{query}"] = "pending"
    
    start_year = request.session.get('start_year', '')
    end_year = request.session.get('end_year', '')
    rank = request.session.get('rank', '')
    
    return render(request, "base.html", {
        "content_template": "search-paper/search-result.html",
        "body_class": "bg-gray-100",
        "show_search_form": True,
        "query": query,
        "years": [],
        "ranks": [],
        "papers": [],
        "start_year": start_year,
        "end_year": end_year,
        "selected_rank": rank
    })

@csrf_protect
@require_GET
def search_api(request):
    query = request.GET.get('query', '').strip()
    start_year = request.GET.get('start_year', '').strip()
    end_year = request.GET.get('end_year', '').strip()
    rank = request.GET.get('rank', '').strip()
    
    if not query:
        logger.warning("Empty query received in search_api")
        return JsonResponse({"error": "Kueri tidak boleh kosong"}, status=400)
    
    if start_year:
        request.session['start_year'] = start_year
    else:
        request.session.pop('start_year', None)
    if end_year:
        request.session['end_year'] = end_year
    else:
        request.session.pop('end_year', None)
    if rank:
        request.session['rank'] = rank
    else:
        request.session.pop('rank', None)
    
    session_key = f"pure_search_{query}"
    last_query = request.session.get('last_search_query', '')
    if session_key in request.session and last_query != query:
        del request.session[session_key]
    
    clear_old_sessions(request, query)
    
    if session_key in request.session:
        papers_data = request.session[session_key]
        time_with_session = 0.0
        time_without_session = 0.0
    else:
        handler = Neo4jHandler()
        try:
            start_time = time.time()
            papers_data, paper_id = handler.perform_search(query)
            time_with_session = (time.time() - start_time) * 1000
            logger.debug(f"Waktu pencarian dengan session untuk query '{query}': {time_with_session:.2f} ms")

            start_time = time.time()
            time_without_session = (time.time() - start_time) * 1000
            logger.debug(f"Waktu pencarian tanpa session untuk query '{query}': {time_without_session:.2f} ms")

            if not papers_data:
                logger.warning(f"No papers found in Neo4j for query: '{query}'")
                return JsonResponse({
                    "papers": [],
                    "years": [],
                    "ranks": ['Semua Peringkat'],
                    "message": f"Kueri pencarian '{query}' tidak menghasilkan artikel ilmiah apapun"
                }, status=200)
            request.session[session_key] = papers_data
            request.session['last_search_query'] = query
            request.session.modified = True
            request.session.save()
        except Exception as e:
            logger.error(f"Error in search_api: {str(e)}")
            return JsonResponse({
                "error": f"Terjadi kesalahan: {str(e)}"
            }, status=500)
        finally:
            handler.close()
    
    years = set()
    ranks = set()
    for paper in papers_data:
        if paper.get('year'):
            try:
                years.add(int(paper['year']))
            except (ValueError, TypeError):
                pass
        elif paper.get('date'):
            date_str = paper['date']
            try:
                for part in date_str.split():
                    if part.isdigit() and len(part) == 4:
                        years.add(int(part))
                        break
                if not years and '-' in date_str:
                    years.add(int(date_str.split('-')[0]))
                if not years and '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        years.add(int(parts[2]))
            except (ValueError, TypeError, IndexError):
                pass
        rank_value = paper.get('rank', 'Tidak Teridentifikasi')
        ranks.add('Tidak Teridentifikasi' if not rank_value or rank_value in ['-', '', None] else rank_value)
    
    years = sorted(list(years), reverse=True)
    ranks = sorted(list(ranks), key=lambda x: x if x != 'Tidak Teridentifikasi' else 'Z')
    if 'Semua Peringkat' not in ranks:
        ranks = ranks
    
    filtered_papers = papers_data
    if start_year and end_year:
        try:
            start_year = int(start_year)
            end_year = int(end_year)
            filtered_papers = [
                paper for paper in filtered_papers
                if paper.get('year') and start_year <= int(paper['year']) <= end_year
            ]
        except ValueError:
            logger.warning("Invalid year filter values")
            filtered_papers = papers_data
    
    if rank and rank != 'Semua Peringkat':
        filtered_papers = [
            paper for paper in filtered_papers
            if (
                (rank == 'Tidak Teridentifikasi' and (paper.get('rank') in [None, '', '-'] or not paper.get('rank')))
                or (paper.get('rank') == rank)
            )
        ]
    
    if not filtered_papers and papers_data:
        logger.debug(f"No papers match filters for query: '{query}', start_year: '{start_year}', end_year: '{end_year}', rank: '{rank}'")
        return JsonResponse({
            "papers": [],
            "years": years,
            "ranks": ranks,
            "message": "Tidak ada paper yang sesuai dengan filter yang dipilih"
        }, status=200)
    
    return JsonResponse({
        "papers": filtered_papers,
        "years": years,
        "ranks": ranks
    }, safe=False)

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