from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from app.utils.neo4j_connection import Neo4jConnection
from app.utils.knowledge_graph_manager import KnowledgeGraphManager
import os
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def generate_knowledge_graph(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_CSV_DIR = os.path.join(BASE_DIR, "data-csv")
    PAPERS_PATH = os.path.join(DATA_CSV_DIR, "papers.csv")
    JOURNALS_PATH = os.path.join(DATA_CSV_DIR, "journalss.csv")
    INSTITUTION_PATH = os.path.join(DATA_CSV_DIR, "perguruan-tinggi.csv")
    REFERENCES_PATH = os.path.join(DATA_CSV_DIR, "references.csv")
    neo4j_connection = None
    manager = None
    
    try:
        neo4j_connection = Neo4jConnection()
        manager = KnowledgeGraphManager(neo4j_connection)

        import_configs = [
            {"type": "institution", "file_path": INSTITUTION_PATH},
            {"type": "journal", "file_path": JOURNALS_PATH},
            {"type": "paper", "file_path": PAPERS_PATH},
            {"type": "author", "file_path": PAPERS_PATH},
            {"type": "journal", "file_path": PAPERS_PATH, "kwargs": {"is_relation": True}},
            {"type": "field_of_study", "file_path": PAPERS_PATH},
            {"type": "publication_type", "file_path": PAPERS_PATH},
            {"type": "reference", "file_path": REFERENCES_PATH},
        ]

        validation_result, importers = manager.import_all(import_configs)

        processed_counts = {
            "papers_processed": next(importer.count_rows() for importer in importers if importer.file_path == PAPERS_PATH and importer.__class__.__name__ == "PaperImporter"),
            "journals_processed": next(importer.count_rows() for importer in importers if importer.file_path == JOURNALS_PATH),
            "institutions_processed": next(importer.count_rows() for importer in importers if importer.file_path == INSTITUTION_PATH),
            "references_processed": next(importer.count_rows() for importer in importers if importer.file_path == REFERENCES_PATH),
        }

        return JsonResponse({
            "message": "Knowledge graph generated successfully",
            **processed_counts,
            "validation": validation_result
        }, status=200)
    except Exception as e:
        logger.error(f"Error generating knowledge graph: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        if manager:
            manager.close_connection()