from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from app.components.search_result import Neo4jHandler, PaperProcessor
import logging

logger = logging.getLogger(__name__)

def index(request):
    topics = []
    neo4j_handler = Neo4jHandler()
    try:
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
                import time; time.sleep(1)  # Penundaan sementara untuk sinkronisasi
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

@require_POST
def apply_date_filter(request):
    try:
        query = request.POST.get('query', '').strip()
        start_date = request.POST.get('start_date', '').strip()
        end_date = request.POST.get('end_date', '').strip()
        page = int(request.POST.get('page', '1'))

        session_key = f"pure_search_{query}"
        papers = request.session.get(session_key, []) or []
        logger.debug(f"Retrieved {len(papers)} papers from session for query: {query}")
        logger.debug(f"Raw papers: {[{'paperId': p['paperId'], 'date': p['date'], 'year': p['year']} for p in papers]}")
        
        filtered_papers = PaperProcessor.filter_papers_by_year(papers, start_date, end_date)
        logger.debug(f"Filtered {len(papers)} papers to {len(filtered_papers)} for {start_date}-{end_date}")

        per_page = 10
        start = (page - 1) * per_page
        end = start + per_page
        paginated_papers = filtered_papers[start:end] or []

        num_pages = max((len(filtered_papers) + per_page - 1) // per_page, 1)
        paginator = {
            'num_pages': num_pages,
            'page_range': list(range(1, num_pages + 1)),
            'has_previous': page > 1,
            'has_next': page < num_pages,
            'previous_page_number': page - 1,
            'next_page_number': page + 1,
            'number': page
        }

        context = {
            'papers': paginated_papers,
            'paginator': paginator,
            'query': query,
            'start_date': start_date,
            'end_date': end_date,
            'is_loading': False,
            'error': '',
            'results_count': len(filtered_papers),
            'years': list(range(2025, 1975, -1))
        }
        result_html = render_to_string('search-paper/search-result.html', context, request=request)

        return JsonResponse({
            'success': True,
            'papers': paginated_papers,
            'result_html': result_html
        })
    except Exception as e:
        logger.error(f"Kesalahan di apply_date_filter: {str(e)}")
        return JsonResponse({
            'success': False,
            'papers': [],
            'error': f"Kesalahan: {str(e)}"
        })

@require_POST
def load_page(request):
    return apply_date_filter(request)