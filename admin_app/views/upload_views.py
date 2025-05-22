import os
import uuid
import logging
import time
import threading
from django.http import JsonResponse, HttpRequest
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from app.views.embedding_views import EmbeddingView
from app.views.preprocessing_views import create_similar_paper_relation, create_page_rank
from app.importers.importer_factory import ImporterFactory
from app.utils.knowledge_graph_manager import KnowledgeGraphManager
from app.utils.neo4j_connection import Neo4jConnection
from admin_app.services.history_service import HistoryService

logger = logging.getLogger(__name__)

process_status = {
    'is_processing': False,
    'step': 0,
    'total_steps': 4,
    'progress_percent': 0,
    'progress_message': '',
    'message': '',
    'log': []
}

@csrf_exempt
def upload_temp_files(request):
    try:
        csv_file = request.FILES.get('csv_file')
        ref_file = request.FILES.get('referensi_csv_file')
        if not csv_file or not ref_file:
            return JsonResponse({'error': 'Both CSV files are required'}, status=400)

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp-import')
        os.makedirs(temp_dir, exist_ok=True)

        csv_filename = f'papers_{uuid.uuid4()}.csv'
        ref_filename = f'refs_{uuid.uuid4()}.csv'
        csv_path = os.path.join(temp_dir, csv_filename)
        ref_path = os.path.join(temp_dir, ref_filename)

        fs = FileSystemStorage(location=temp_dir)
        fs.save(csv_filename, csv_file)
        fs.save(ref_filename, ref_file)

        return JsonResponse({'status': 'success', 'csv_path': csv_path, 'ref_path': ref_path})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def start_import(request):
    global process_status
    try:
        csv_path = request.POST.get('csv_path')
        ref_path = request.POST.get('ref_path')
        if not csv_path or not ref_path:
            return JsonResponse({'error': 'CSV and reference paths required'}, status=400)

        if process_status['is_processing']:
            return JsonResponse({'error': 'Another process is running'}, status=400)
        
        # intial history
        history_service = HistoryService()
        history_record = history_service.add_history(
            operation_type="import",
            details={
                "csv_file": os.path.basename(csv_path),
                "ref_file": os.path.basename(ref_path),
                "start_time": time.strftime('%Y-%m-%d %H:%M:%S')
            },
            status="in_progress"
        )

        process_status = {
            'is_processing': True,
            'step': 0,
            'total_steps': 4,
            'progress_percent': 0,
            'progress_message': 'Starting the import process...',
            'message': '',
            'log': [f"[{time.strftime('%H:%M:%S')}] Starting the import process..."],
            'history_id': history_record.get('id') if history_record else None
        }

        def process_files():
            global process_status
            import_stats = {
                "papers": 0,
                "authors": 0,
                "publication_types": 0,
                "fields_of_study": 0
            }
            
            try:
                # Step 1: Import CSV
                process_status['step'] = 1
                process_status['progress_percent'] = 25
                process_status['progress_message'] = 'Importing CSV data...'
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Importing CSV data...")
                neo4j_conn = Neo4jConnection()
                kg_manager = KnowledgeGraphManager(neo4j_conn)
                
                import_configs = [
                    {"type": "paper", "file_path": csv_path},
                    {"type": "author", "file_path": csv_path},
                    {"type": "journal", "file_path": csv_path, "kwargs": {"is_relation": True}},
                    {"type": "field_of_study", "file_path": csv_path},
                    {"type": "publication_type", "file_path": csv_path},
                    {"type": "reference", "file_path": ref_path},
                ]
                
                # Add stats to import_stats
                stats = kg_manager.validate_graph()
                import_stats = {
                    "papers": stats["total_papers"],
                    "authors": stats["total_authors"],
                    "publication_types": stats["total_publication_type"],
                    "fields_of_study": stats["total_fields_of_study"]
                }

                try:
                    validation_result = kg_manager.import_all(import_configs)
                    process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Successfully imported CSV: {validation_result}")
                except Exception as e:
                    raise Exception(f"CSV import failed: {str(e)}")
                finally:
                    kg_manager.close_connection()
                time.sleep(1)

                # Step 2: Generate embeddings
                process_status['step'] = 2
                process_status['progress_percent'] = 50
                process_status['progress_message'] = 'Generating embeddings...'
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Generating embeddings...")
                embedding_response = EmbeddingView().post(None)
                if embedding_response and hasattr(embedding_response, 'status_code') and embedding_response.status_code != 200:
                    raise Exception("Failed to generate embeddings")
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Successfully generated embeddings")
                time.sleep(1)

                # Step 3: Calculate similarities
                process_status['step'] = 3
                process_status['progress_percent'] = 75
                process_status['progress_message'] = 'Calculating similarities...'
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Calculating similarities...")
                similarity_response = create_similar_paper_relation(None)
                if similarity_response and hasattr(similarity_response, 'status_code') and similarity_response.status_code != 200:
                    raise Exception(f"Failed to calculate similarities: {similarity_response.get('error', 'Unknown error')}")
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Successfully calculated similarities")
                time.sleep(1)

                # Step 4: Calculate PageRank
                process_status['step'] = 4
                process_status['progress_percent'] = 100
                process_status['progress_message'] = 'Calculating PageRank...'
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Calculating PageRank...")
                pagerank_response = create_page_rank(None)
                if pagerank_response and hasattr(pagerank_response, 'status_code') and pagerank_response.status_code != 200:
                    raise Exception("Failed to calculate PageRank")
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Successfully calculated PageRank")
                time.sleep(1)

                process_status['message'] = 'Import dan proses selesai.'
                process_status['progress_message'] = 'Proses selesai!'
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Import dan proses selesai.")
                
                if process_status.get('history_id'):
                    history_service = HistoryService()
                    history_service.update_history(
                    process_status['history_id'],
                    details={
                        "csv_file": os.path.basename(csv_path),
                        "ref_file": os.path.basename(ref_path),
                        "start_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "end_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "stats": import_stats
                    },
                    status="success"
                )
                
            except Exception as e:
                process_status['message'] = f'Error in step {process_status["step"]}: {str(e)}'
                process_status['progress_message'] = f'Error: {str(e)}'
                process_status['log'].append(f"[{time.strftime('%H:%M:%S')}] Error in step {process_status['step']}: {str(e)}")
            finally:
                process_status['is_processing'] = False
                for path in [csv_path, ref_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except Exception as e:
                            logger.error(f"Failed to delete {path}: {str(e)}")

        thread = threading.Thread(target=process_files)
        thread.daemon = True
        thread.start()

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def get_progress(request):
    global process_status
    return JsonResponse(process_status)