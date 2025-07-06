from django.shortcuts import render
from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging
from neomodel import db
from django.http import JsonResponse

logger = logging.getLogger(__name__)

def access_history(request):
    return render(request, "base.html", {
        "content_template": "access-history-recommendation/index.html",
        "body_class": "bg-gray-100",
        "show_search_form": False,
    })
    
def get_recommendation_by_access(user_id):
    try:
        query = """
            MATCH (u:User {userId: $userId})-[r_read:HAS_READ]->(:Paper)-[r_sim:HIGHEST_SIMILAR]->(p:Paper)
            WHERE NOT (u)-[:HAS_READ]->(p)
            WITH p, r_sim, max(r_read.read_at) AS newest_read
            ORDER BY newest_read DESC, r_sim.score DESC, p.pagerank DESC
            OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
            RETURN 
                p.title AS title,
                p.paperId AS paperId,
                p.abstract AS abstract, 
                p.publicationDate AS date,
                p.year AS year,
                p.pagerank AS pagerank, 
                r_sim.score AS score,
                collect(DISTINCT author.name) AS authors
        """
        results, meta = db.cypher_query(query, {'userId': user_id})
        papers_raw = [dict(zip(meta, row)) for row in results]
        
        processed_papers = []
        for record in papers_raw:
            record["date"] = format_date_to_indonesian(
                record.get("date"), 
                fallback_year=record.get("year", "N/A")
            )
            processed_papers.append(record)
            
        return processed_papers
        
    except Exception as e:
        logger.error(f"Error in get_recommendation_by_access: {str(e)}")
        return []

def recommendation_by_access_api(request):
    try:
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({
                "error": "Parameter userId diperlukan"
            }, status=400)

        papers = get_recommendation_by_access(user_id)
        
        if not papers:
            logger.warning(f"Tidak ada rekomendasi untuk userId: {user_id}")
            return JsonResponse({
                "papers": [],
                "message": f"Tidak ada rekomendasi untuk userId: {user_id}"
            }, status=200)

        return JsonResponse({
            "papers": papers
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error in recommendation_by_access_api: {str(e)}")
        return JsonResponse({
            "error": f"Terjadi kesalahan: {str(e)}"
        }, status=500)