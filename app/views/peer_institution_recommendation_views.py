from django.shortcuts import render
from app.utils.parse_indonesian_date import format_date_to_indonesian
import logging
from neomodel import db
from django.http import JsonResponse
from app.models import User

logger = logging.getLogger(__name__)

def peer_institution(request):
    return render(request, "base.html", {
        "content_template": "peer-institution-recommendation/index.html",
        "body_class": "bg-gray-100",
        "show_search_form": False,
    })
    
def get_peer_recommendations(user_id):
    try:
        current_user = User.nodes.get(userId=user_id)
        institution_node = current_user.affiliated_with.get_or_none()
        if not institution_node:
            logger.warning(f"Tidak ada institusi untuk userId: {user_id}")
            return []

        institutionId = institution_node.institutionId
        query = """
            MATCH (pt:Institution {institutionId: $institutionId})<-[:AFFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
            WHERE NOT EXISTS {
              MATCH (currentUser:User {userId: $userId})-[:HAS_READ]->(p)
            }
            WITH p, count(u) AS jumlahPembaca,
                CASE
                  WHEN p.publicationDate IS NOT NULL AND p.publicationDate CONTAINS '-' 
                    THEN date(left(p.publicationDate, 10))
                  WHEN p.publicationDate IS NOT NULL AND p.publicationDate CONTAINS '/' 
                    THEN date(datetime({epochMillis: apoc.date.parse(split(p.publicationDate, ' ')[0], 'ms', 'M/d/yyyy')}))
                  ELSE null
                END AS normalizedDate
            ORDER BY jumlahPembaca DESC, normalizedDate DESC, p.year DESC
            LIMIT 30
            OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
            RETURN 
                p.title AS title,
                p.paperId AS paperId,
                p.abstract AS abstract, 
                jumlahPembaca,
                p.publicationDate AS date,
                p.year AS year,
                p.pagerank AS pagerank,
                collect(DISTINCT author.name) AS authors
        """
        params = {'institutionId': institutionId, 'userId': user_id}
        results, meta = db.cypher_query(query, params)
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
        logger.error(f"Error di get_peer_recommendations: {str(e)}", exc_info=True)
        return []

def peer_recommendation_api(request):
    try:
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({
                "error": "Parameter userId diperlukan"
            }, status=400)

        papers = get_peer_recommendations(user_id)
        
        if not papers:
            logger.warning(f"Tidak ada rekomendasi untuk userId: {user_id}")
            return JsonResponse({
                "papers": [],
                "message": f"Tidak ada rekomendasi untuk userId: {user_id} atau pengguna tidak terafiliasi dengan institusi"
            }, status=200)

        return JsonResponse({
            "papers": papers
        }, status=200)
        
    except Exception as e:
        logger.error(f"Error di peer_recommendation_api: {str(e)}")
        return JsonResponse({
            "error": f"Terjadi kesalahan: {str(e)}"
        }, status=500)