import logging
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.services.embedding_services import EmbeddingService  # Import dari services.py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class EmbeddingView(View):
    """
    Class-based view untuk menangani pembuatan dan penyimpanan search embedding.
    """
    def post(self, request):
        embedding_service = EmbeddingService()

        try:
            # Langkah 1: Ambil data paper tanpa embedding
            papers_data = embedding_service.get_paper_without_embedding()
            if not papers_data:
                logger.info("No papers found without search_embedding")
                return JsonResponse({"message": "No papers found without search embedding"}, status=200)

            # Langkah 2: Buat embedding
            embeddings_list = embedding_service.create_embeddings(papers_data)

            # Langkah 3: Simpan embedding ke database
            success_count, error_count = embedding_service.save_embeddings(papers_data, embeddings_list)

            # Langkah 4: Return response
            message = f"Updated search embeddings for {success_count} papers. Errors: {error_count}"
            logger.info(message)
            return JsonResponse({
                "message": message,
                "success_count": success_count,
                "error_count": error_count
            }, status=200)

        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(error_message)
            return JsonResponse({"error": error_message}, status=500)
