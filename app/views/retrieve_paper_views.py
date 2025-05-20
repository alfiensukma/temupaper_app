import os
import io
import csv
import json
import logging
import zipfile
import traceback
from semanticscholar import SemanticScholar
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime

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

@csrf_exempt
def fetch_papers(request):
    try:
        if request.method != "GET":
            return JsonResponse({"error": "Method not allowed"}, status=405)

        query = request.GET.get('query', '')
        min_year = int(request.GET.get('min_year', 2020))
        fields_of_study = request.GET.get('fields_of_study', 'Computer Science')
        reference_limit = request.GET.get('reference_limit', 100)
        limit = int(request.GET.get('limit', 100))

        reference_limit = int(reference_limit) if reference_limit is not None else None
        if limit > 1000:
            limit = 1000

        # Get data paper from Semantic Scholar
        results = sch.search_paper(
            query, year=f"{min_year}-", limit=limit,
            fields_of_study=[fields_of_study],
            fields=['paperId', 'corpusId', 'externalIds', 'authors', 'title', 'year', 'abstract', 'url', 'publicationDate', 'fieldsOfStudy', 's2FieldsOfStudy', 'venue', 'publicationVenue', 'citationCount', 'influentialCitationCount', 'publicationTypes', 'journal', 'citationStyles', 'embedding', 'references', 'referenceCount']
        )

        if not results:
            return JsonResponse({"message": "No papers found", "data": []}, status=200)

        # Filter
        paper_data = [
            create_paper_info(paper, include_references=True, reference_limit=reference_limit)
            for paper in results
            if paper.year and paper.year >= min_year and paper.abstract and paper.fieldsOfStudy and paper.embedding
        ][:limit]

        if not paper_data:
            return JsonResponse({"message": "No papers found after filtering", "data": []}, status=200)

        references_list = [
            {"source_id": paper["paperId"], "target_id": ref_id}
            for paper in paper_data for ref_id in paper.get("reference_id", [])
        ]

        # --- Generate folder & file name ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = timestamp
        folder_path = os.path.join("app", "data-csv", folder_name)
        os.makedirs(folder_path, exist_ok=True)

        papers_filename = f"papers-{timestamp}.csv"
        references_filename = f"references-{timestamp}.csv"
        papers_path = os.path.join(folder_path, papers_filename)
        references_path = os.path.join(folder_path, references_filename)

        # --- Save to CSV (overwrite, no append) ---
        paper_fieldnames = [
            "paperId", "corpusId", "externalIds", "authors", "title", "year", "abstract", "url",
            "publicationDate", "fieldsOfStudy", "s2FieldsOfStudy", "venue", "publicationVenue",
            "citationCount", "influentialCitationCount", "publicationTypes", "journal",
            "citationStyles", "embedding", "referenceCount"
        ]
        reference_fieldnames = ["source_id", "target_id"]

        save_to_csv(papers_path, paper_data, paper_fieldnames, mode='w')
        save_to_csv(references_path, references_list, reference_fieldnames, mode='w')

        # --- Prepare ZIP for download ---
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
        logger.error(f"Error in fetch_papers: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({"error": str(e)}, status=500)