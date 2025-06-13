import os
import io
import csv
import json
import logging
import zipfile
import traceback
import shutil
from semanticscholar import SemanticScholar
from semanticscholar.Paper import Paper
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from app.utils.neo4j_connection import Neo4jConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

original_paper_init = Paper.__init__
def patched_paper_init(self, data):
    if data.get('references') is None:
        data['references'] = []
    
    if data.get('citations') is None:
        data['citations'] = []

    original_paper_init(self, data)

Paper.__init__ = patched_paper_init
logger.info("Monkey patch applied to semanticscholar.Paper to handle None for references/citations.")

# init
sch = SemanticScholar()
CSV_PATH = "app/data-csv"
PAPERS_PATH = os.path.join(CSV_PATH, "papers.csv")
PAPER_REFERENCES_PATH = os.path.join(CSV_PATH, "paper-references.csv")
REFERENCES_PATH = os.path.join(CSV_PATH, "references.csv")

if not os.path.exists(CSV_PATH):
    os.makedirs(CSV_PATH)

# Function to save data paper to CSV
def save_to_csv(file_path, data, fieldnames, mode='w'):
    with open(file_path, mode=mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, extrasaction='ignore')
        if mode == 'w' or (mode == 'a' and os.stat(file_path).st_size == 0):
            writer.writeheader()
        for row in data:
            csv_row = {key: str(row.get(key, '')) for key in fieldnames}
            if 'reference_id' in csv_row:
                csv_row['reference_id'] = ';'.join(csv_row['reference_id']) if csv_row['reference_id'] else ''
            writer.writerow(csv_row)
            
# Helper function to create paper info dictionary
def create_paper_info(paper, include_references=False, reference_limit=None):
    try:
        s2_fields = []
        if hasattr(paper, 's2FieldsOfStudy') and paper.s2FieldsOfStudy:
            s2_fields = [f"{field['category']}" for field in paper.s2FieldsOfStudy if isinstance(field, dict) and 'category' in field]
        
        authors_data = []
        if hasattr(paper, 'authors') and paper.authors:
            authors_data = [
                {"authorId": str(author.authorId), "name": str(author.name).strip()}
                for author in paper.authors 
                if hasattr(author, 'authorId') and author.authorId
            ]
        
        paper_info = {
            "paperId": str(getattr(paper, 'paperId', '') or ''),
            "corpusId": str(getattr(paper, 'corpusId', '') or ''),
            "externalIds": str(getattr(paper, 'externalIds', '') or ''),
            "authors": json.dumps(authors_data),
            "title": str(getattr(paper, 'title', '') or ''),
            "year": str(getattr(paper, 'year', '') or ''),
            "abstract": str(getattr(paper, 'abstract', '') or ''),
            "url": str(getattr(paper, 'url', '') or ''),
            "publicationDate": str(getattr(paper, 'publicationDate', '') or ''),
            "fieldsOfStudy": ";".join(getattr(paper, 'fieldsOfStudy', []) or []),
            "s2FieldsOfStudy": ";".join(s2_fields),
            "venue": str(getattr(paper, 'venue', '') or ''),
            "publicationVenue": str(getattr(paper, 'publicationVenue', '') or ''),
            "citationCount": str(getattr(paper, 'citationCount', 0) or 0),
            "influentialCitationCount": str(getattr(paper, 'influentialCitationCount', 0) or 0),
            "publicationTypes": ";".join(getattr(paper, 'publicationTypes', []) or []),
            "journal": str(getattr(paper, 'journal', '') or ''),
            "citationStyles": str(getattr(paper, 'citationStyles', '') or ''),
            "embedding": json.dumps(paper.embedding.get('vector', []) if getattr(paper, 'embedding', None) else []),
            "referenceCount": str(getattr(paper, 'referenceCount', 0) or 0),
        }
        
        if include_references:
            refs = []
            try:
                if hasattr(paper, 'references') and paper.references:
                    refs = [
                        ref.paperId 
                        for ref in paper.references 
                        if ref and hasattr(ref, 'paperId') and ref.paperId
                    ]
                    logger.debug(f"Found {len(refs)} valid references for paper {paper.paperId}")
            except Exception as ref_error:
                logger.warning(f"Error processing references for paper {paper.paperId}: {str(ref_error)}")
                refs = []
            
            paper_info["reference_id"] = refs[:reference_limit] if reference_limit is not None else refs

        return paper_info
    except Exception as e:
        logger.error(f"Error creating paper info: {str(e)}")
        return None

# Get current paper count and update topic in Neo4j
def manage_topic(topic_id, topic_name, papers_found=0, update=False):
    try:
        neo4j_conn = Neo4jConnection().get_driver()
        with neo4j_conn.session() as session:
            if not update:
                result = session.run("""
                    MATCH (t:Topic {topicId: $topic_id}) 
                    RETURN t.paperCount as currentCount
                """, topic_id=topic_id)
                
                record = result.single()
                return record["currentCount"] if record and "currentCount" in record else 0
            else:
                result = session.run("""
                    MATCH (t:Topic {topicId: $topic_id})
                    SET t.paperCount = COALESCE(t.paperCount, 0) + $papers_found,
                        t.lastUpdated = $timestamp
                    RETURN t.paperCount as newCount
                """, topic_id=topic_id, papers_found=papers_found, timestamp=datetime.now().isoformat())
                
                record = result.single()
                return record["newCount"] if record and "newCount" in record else papers_found
    except Exception as e:
        logger.error(f"Error managing topic: {str(e)}")
        return 0 if not update else papers_found
    finally:
        if 'neo4j_conn' in locals() and neo4j_conn:
            neo4j_conn.close()

@csrf_exempt
def scrape_topic(request):
    folder_path = None
    
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)
        
        topic_id = request.GET.get('topic_id', '')  
        topic_name = request.GET.get('topic_name', '') 
        
        if not topic_id or not topic_name:
            return JsonResponse({"error": "topic_id dan topic_name diperlukan"}, status=400)
            
        query = topic_name
        min_year = int(request.GET.get('min_year', 2020))
        fields_of_study = request.GET.get('fields_of_study', 'Computer Science')
        reference_limit = request.GET.get('reference_limit', 100)
        limit = int(request.GET.get('limit', 100))
        csv_timestamp = request.GET.get('csv_timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))

        timestamp = csv_timestamp
        folder_name = timestamp
        folder_path = os.path.join("app", "data-csv", folder_name)
        os.makedirs(folder_path, exist_ok=True)

        papers_filename = f"papers-{timestamp}.csv"
        references_filename = f"references-{timestamp}.csv"
        papers_path = os.path.join(folder_path, papers_filename)
        references_path = os.path.join(folder_path, references_filename)

        paper_fieldnames = [
            "paperId", "corpusId", "externalIds", "authors", "title", "year", "abstract", "url",
            "publicationDate", "fieldsOfStudy", "s2FieldsOfStudy", "venue", "publicationVenue",
            "citationCount", "influentialCitationCount", "publicationTypes", "journal",
            "citationStyles", "embedding", "referenceCount"
        ]
        reference_fieldnames = ["source_id", "target_id"]
        
        current_count = manage_topic(topic_id, topic_name)
        
        # check if limit is exceeded
        if current_count >= 1000:
            return JsonResponse({
                "error": f"Batas maksimum 1000 paper untuk topik '{topic_name}' telah tercapai. Silakan coba topik lain."
            }, status=400)
        
        logger.info(f"Fetching papers for topic '{query}' with current count {current_count}")
        
        # decide how many pages to skip
        pages_to_skip = current_count // limit
        
        paginated_results = sch.search_paper(
            query, year=f"{min_year}-", limit=limit,
            fields_of_study=[fields_of_study],
            fields=['paperId', 'corpusId', 'externalIds', 'authors', 'title', 'year', 'abstract', 'url', 'publicationDate', 'fieldsOfStudy', 's2FieldsOfStudy', 'venue', 'publicationVenue', 'citationCount', 'influentialCitationCount', 'publicationTypes', 'journal', 'citationStyles', 'embedding', 'references', 'referenceCount']
        )
        
        results = paginated_results
        current_page = 0
        
        # Semantic Scholar next_page() method
        while current_page < pages_to_skip and hasattr(results, 'next_page') and callable(results.next_page):
            results = results.next_page()
            current_page += 1
            logger.info(f"Skipped page {current_page} for topic '{query}'")
        
        # papers_result = list(results) if results else []
        
        papers_result = []
        if results:
            logger.info("Iterating through search results to safely handle potential data errors...")
            for paper_item in results:
                try:
                    papers_result.append(paper_item)
                except TypeError as e:
                    if "'NoneType' object is not iterable" in str(e):
                        logger.warning(f"Skipping a paper due to malformed data (likely 'references' is None). Error: {e}")
                    else:
                        logger.error(f"An unexpected TypeError occurred while processing a paper: {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while processing a paper item: {e}")
        
        if not papers_result:
            return JsonResponse({
                "status": "empty",
                "topic": topic_name,
                "count": 0,
                "message": "No papers found",
                "timestamp": timestamp
            })

        # Filter
        paper_data = []
        for paper in papers_result:
            try:
                required_fields = {
                    'title': getattr(paper, 'title', None),
                    'abstract': getattr(paper, 'abstract', None),
                    'embedding': getattr(paper, 'embedding', None)
                }

                has_references = False
                try:
                    if hasattr(paper, 'references') and paper.references is not None:
                        has_references = True
                except Exception as ref_error:
                    logger.warning(f"Error checking references for paper: {str(ref_error)}")

                if not all(required_fields.values()):
                    logger.info(f"Skipping paper '{required_fields['title'] or 'Untitled'}': Missing required fields")
                    logger.debug(f"Missing fields: {[k for k,v in required_fields.items() if not v]}")
                    continue

                paper_info = create_paper_info(paper, include_references=has_references, reference_limit=reference_limit)
                if paper_info:
                    paper_data.append(paper_info)
                    
            except Exception as e:
                logger.warning(f"Error processing paper: {str(e)}")
                continue

        paper_data = paper_data[:limit]

        if not paper_data:
            return JsonResponse({
                "status": "empty",
                "topic": topic_name,
                "count": 0,
                "message": "No papers found after filtering",
                "timestamp": timestamp
            })

        references_list = [
            {"source_id": paper["paperId"], "target_id": ref_id}
            for paper in paper_data for ref_id in paper.get("reference_id", [])
        ]

        # Save to CSV mode append ('a') if file exists, else write ('w')
        papers_mode = 'w' if not os.path.exists(papers_path) else 'a'
        references_mode = 'w' if not os.path.exists(references_path) else 'a'
        
        save_to_csv(papers_path, paper_data, paper_fieldnames, mode=papers_mode)
        save_to_csv(references_path, references_list, reference_fieldnames, mode=references_mode)
        
        papers_found = len(paper_data)
        
        new_count = manage_topic(topic_id, topic_name, papers_found, update=True)
        
        return JsonResponse({
            "status": "success",
            "topic": topic_name,
            "count": papers_found,
            "current_count": current_count,
            "new_count": new_count,
            "message": f"Berhasil mendapatkan {papers_found} paper",
            "timestamp": timestamp
        })

    except Exception as e:
        logger.error(f"Error in scrape_topic: {str(e)}\n{traceback.format_exc()}")
        try:
            if folder_path and os.path.exists(folder_path):
                is_first_topic = not any(
                    f.endswith('.csv') for f in os.listdir(folder_path)
                )
                
                # if folder_path and is_first_topic:
                if is_first_topic:
                    logger.info(f"Deleting folder due to error: {folder_path}")
                    shutil.rmtree(folder_path)
                else:
                    logger.info(f"Not deleting folder {folder_path} as it may contain data from other topics")
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up folder: {cleanup_error}")
        
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def download_results(request):
    folder_path = None
    
    try:
        timestamp = request.GET.get('timestamp')
        if not timestamp:
            return JsonResponse({"error": "Timestamp required"}, status=400)
        
        folder_path = os.path.join("app", "data-csv", timestamp)
        if not os.path.exists(folder_path):
            return JsonResponse({"error": f"No data found for timestamp {timestamp}"}, status=404)
        
        papers_filename = f"papers-{timestamp}.csv"
        references_filename = f"references-{timestamp}.csv"
        papers_path = os.path.join(folder_path, papers_filename)
        references_path = os.path.join(folder_path, references_filename)
        
        if not os.path.exists(papers_path) or not os.path.exists(references_path):
            return JsonResponse({"error": "CSV files not found"}, status=404)
        
        # zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            with open(papers_path, 'r', encoding='utf-8') as f:
                zip_file.writestr(papers_filename, f.read())
            with open(references_path, 'r', encoding='utf-8') as f:
                zip_file.writestr(references_filename, f.read())
            
        zip_buffer.seek(0)
        
        response = FileResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="scraping_{timestamp}.zip"'

        # Delete the folder
        try:
            shutil.rmtree(folder_path)
            logger.info(f"Successfully deleted folder: {folder_path}")
        except Exception as cleanup_error:
            logger.warning(f"Error deleting folder {folder_path}: {cleanup_error}")

        return response

    except Exception as e:
        logger.error(f"Error in download_results: {str(e)}\n{traceback.format_exc()}")
        if folder_path and os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
                logger.info(f"Cleaned up folder after error: {folder_path}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up folder: {cleanup_error}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def fetch_papers(request):
    try:
        response = scrape_topic(request)
        if response.status_code == 200:
            data = json.loads(response.content)
            timestamp = data.get("timestamp")
            if timestamp:
                download_request = request.__class__()
                download_request.method = "GET"
                download_request.GET = {"timestamp": timestamp}
                return download_results(download_request)
        return response
    except Exception as e:
        logger.error(f"Error in fetch_papers: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({"error": str(e)}, status=500)