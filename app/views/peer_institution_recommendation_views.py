from django.shortcuts import render
from django.core.paginator import Paginator
from app.models import User
from datetime import datetime
import logging
from neomodel  import db

logger = logging.getLogger(__name__)

def peer_institution(request):
    if not request.session.get('is_authenticated', False):
        return render(request, "base.html", {
            "content_template": "peer-institution-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": "Anda perlu login untuk melihat halaman ini"
        })
    
    user_id = request.session.get('user_id')
    
    try:
        # Mendapatkan informasi user dan institusi
        current_user = User.nodes.get(userId=user_id)
        institutions = current_user.affiliated_with.all()
        institution = institutions[0]
        institutionId = institution.institutionId
        
        # Menggunakan Cypher query via neomodel
        query = """
            MATCH (pt:Institution {institutionId: $institutionId})<-[:AFFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
            WITH p, count(u) AS jumlahPembaca
            OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
            RETURN 
                p.title AS title,
                p.paperId as paperId,
                p.abstract as abstract, 
                jumlahPembaca,
                p.publicationDate AS date,
                p.year AS year,
                collect(DISTINCT author.name) AS authors
            ORDER BY jumlahPembaca DESC, p.publicationDate DESC, p.year DESC
            LIMIT 10
        """
        
        results, meta = db.cypher_query(query, {'institutionId': institutionId})
        
        # Transformasi data hasil query
        papers = []
        for row in results:
            papers.append({
                "paperId": row[1],
                "title": row[0],
                "abstract": row[2],
                "date": row[4],
                "year": row[5],
                "authors": row[6]
            })
            
        # Memformat tanggal untuk paper
        for paper in papers:
            if paper["date"]:
                try:
                    try:
                        dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        dt = datetime.strptime(paper["date"], "%Y-%m-%d")
                    paper["date"] = dt.strftime("%d %B %Y")
                except Exception as e:
                    logger.error(f"Date parse error for paper {paper['paperId']}: {e}")
                    paper["date"] = paper.get("year", "Unknown date")
            else:
                paper["date"] = paper.get("year", "Unknown date")

        # Paginasi hasil
        paginator = Paginator(papers, 5)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Render halaman dengan data
        return render(request, "base.html", {
            "content_template": "peer-institution-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "page_obj": page_obj,
        })
    
    except Exception as e:
        logger.error(f"Error in peer_institution view: {str(e)}")
        return render(request, "base.html", {
            "content_template": "peer-institution-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        })