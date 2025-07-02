from django.http import HttpResponse
from app.services.graph_processor_services import GraphPreprocessorService
import logging

logger = logging.getLogger(__name__)

def create_similar_paper_relation(request):
    service = None
    try:
        service = GraphPreprocessorService()
        service.run_similarity_calculations()
        return HttpResponse("Proses pembuatan relasi similaritas berhasil.", status=200)
    except Exception as e:
        logger.exception("Gagal saat membuat relasi similaritas")
        return HttpResponse(f"Error: {e}", status=500)
    finally:
        if service:
            service.close()

def create_page_rank(request):
    service = None
    try:
        service = GraphPreprocessorService()
        service.run_pagerank_calculation()
        return HttpResponse("Proses kalkulasi PageRank berhasil.", status=200)
    except Exception as e:
        logger.exception("Gagal saat menghitung PageRank")
        return HttpResponse(f"Error: {e}", status=500)
    finally:
        if service:
            service.close()