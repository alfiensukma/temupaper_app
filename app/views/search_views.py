from django.shortcuts import render
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
                WHERE t.paperCount IS NOT NULL AND t.paperCount > 0
                RETURN t.name AS topic_name, t.paperCount AS paper_count
                ORDER BY rand()
                LIMIT 5
            """)
            topics = [{"name": record["topic_name"], "count": record["paper_count"]} for record in result]
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
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    state = request.GET.get('state', '')
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    if state != 'loaded' and query:
        keys_to_delete = [key for key in request.session.keys() 
                         if key.startswith('pure_search_') or 
                         key in ['current_query', 'query', 'start_date', 'end_date', 'page']]
        for key in keys_to_delete:
            try:
                del request.session[key]
            except KeyError:
                pass
        request.session.modified = True
        logger.info(f"Cleared session for new query: {query}")

    logger.info(f"Rendering search page: query={query}, state={state}")
    return render(request, "base.html", {
        "content_template": "search-paper/search-result.html",
        "body_class": "bg-gray-100",
        "show_search_form": True,
        "query": query,
        "start_date": start_date,
        "end_date": end_date,
        "is_loading": True,
        "papers": [],
        "paginator": None,
        "page": page,
        "state": state
    })

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