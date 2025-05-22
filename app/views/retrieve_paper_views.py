import os
import io
import csv
import json
import logging
import zipfile
import traceback
import shutil
from semanticscholar import SemanticScholar
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from app.utils.neo4j_connection import Neo4jConnection

# init
sch = SemanticScholar()
CSV_PATH = "app/data-csv"
PAPERS_PATH = os.path.join(CSV_PATH, "papers.csv")
PAPER_REFERENCES_PATH = os.path.join(CSV_PATH, "paper-references.csv")
REFERENCES_PATH = os.path.join(CSV_PATH, "references.csv")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    s2_fields = [f"{field['category']}" for field in (paper.s2FieldsOfStudy or []) if 'category' in field] if hasattr(paper, 's2FieldsOfStudy') else []
    
    authors_data = [
        {"authorId": str(author.authorId), "name": str(author.name).strip()}
        for author in (paper.authors or []) if hasattr(author, 'authorId') and author.authorId
    ]
    
    paper_info = {
        "paperId": str(paper.paperId or ""),
        "corpusId": str(paper.corpusId or ""),
        "externalIds": str(paper.externalIds or ""),
        "authors": json.dumps(authors_data),
        "title": str(paper.title or ""),
        "year": str(paper.year or ""),
        "abstract": str(paper.abstract or ""),
        "url": str(paper.url or ""),
        "publicationDate": str(paper.publicationDate or ""),
        "fieldsOfStudy": ";".join(paper.fieldsOfStudy or []),
        "s2FieldsOfStudy": ";".join(s2_fields),
        "venue": str(paper.venue or ""),
        "publicationVenue": str(paper.publicationVenue or ""),
        "citationCount": str(paper.citationCount or 0),
        "influentialCitationCount": str(paper.influentialCitationCount or 0),
        "publicationTypes": ";".join(paper.publicationTypes or []),
        "journal": str(paper.journal or ""),
        "citationStyles": str(paper.citationStyles or ""),
        "embedding": json.dumps(paper.embedding['vector'] if paper.embedding and 'vector' in paper.embedding else []),
        "referenceCount": str(paper.referenceCount or 0),
    }
    if include_references and hasattr(paper, 'references'):
        refs = paper.references or []
        ref_ids = [ref.paperId for ref in refs if ref.paperId]
        paper_info["reference_id"] = ref_ids[:reference_limit] if reference_limit is not None and reference_limit >= 0 else ref_ids
    return paper_info

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
        
        papers_result = list(results) if results else []
        
        if not papers_result:
            return JsonResponse({
                "status": "empty",
                "topic": topic_name,
                "count": 0,
                "message": "No papers found",
                "timestamp": timestamp
            })

        # Filter
        paper_data = [
            create_paper_info(paper, include_references=True, reference_limit=reference_limit)
            for paper in papers_result
            if paper.year and paper.year >= min_year and paper.abstract and paper.fieldsOfStudy and paper.embedding
        ][:limit]

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
        return response

    except Exception as e:
        logger.error(f"Error in download_results: {str(e)}\n{traceback.format_exc()}")
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