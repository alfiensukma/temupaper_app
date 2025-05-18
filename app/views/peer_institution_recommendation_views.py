from django.shortcuts import render
from django.core.paginator import Paginator
from app.models import User
from datetime import datetime
import logging
from app.utils.neo4j_connection import Neo4jConnection

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

        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()
        
        with driver.session() as session:
            result = session.run("""
                MATCH (pt:Institution {institutionId: $institutionId})<-[:AFFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
                WHERE NOT EXISTS {
                    MATCH (currentUser:User {userId: $userId})-[:HAS_READ]->(p)
                }
                WITH p, count(u) AS jumlahPembaca
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    p.title AS title,
                    p.paperId as paperId,
                    p.abstract as abstract, 
                    jumlahPembaca,
                    p.publicationDate AS date,
                    p.year AS year,
                    p.pagerank as pagerank,
                    collect(DISTINCT author.name) AS authors
                ORDER BY jumlahPembaca DESC, p.pagerank DESC, p.publicationDate DESC, p.year DESC
                LIMIT 10
            """, institutionId=institutionId, userId=user_id) 

            papers = [{
                "paperId": record["paperId"],
                "title": record["title"],
                "date": record["date"],
                "abstract": record["abstract"],
                "authors": record["authors"],
                "year": record["year"]
            } for record in result]       

            for paper in papers:
                if paper["date"]:
                    try:
                        date_str = paper["date"]
                        # Format "m/d/yyyy 0:00" atau "m/d/yyyy"
                        if '/' in date_str:
                            date_str = date_str.split()[0]
                            month, day, year = map(int, date_str.split('/'))
                            dt = datetime(year, month, day)
                            paper["date"] = dt.strftime("%d %B %Y")
                        # Format "yyyy-mm-dd"
                        elif '-' in date_str:
                            dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                            paper["date"] = dt.strftime("%d %B %Y")
                        else:
                            paper["date"] = paper["year"]
                    except Exception as e:
                        logger.error(f"Error formatting date '{paper['date']}': {str(e)}")
                        paper["date"] = paper["date"]

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
    finally:
        if driver:
            driver.close()