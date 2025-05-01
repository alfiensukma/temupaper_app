from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime
from app.utils.neo4j_connection import get_neo4j_driver
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def peer_institution(request):
    driver = None

    try:
        driver = get_neo4j_driver()

        pt_id = "PT_pw13cn"
        
        with driver.session() as session:
            result = session.run("""
                MATCH (pt:Institution {institutionId: $ptId})<-[:AFILIATED_WITH]-(u:User)-[:HAS_READ]->(p:Paper)
                WITH p, count(u) AS jumlahPembaca
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN p.title AS title,
                    p.paperId as paperId,
                    p.abstract as abstract, 
                    jumlahPembaca,
                    p.publicationDate AS date,
                    p.year AS year,
                    collect(DISTINCT author.name) AS authors
                ORDER BY jumlahPembaca DESC, p.publicationDate DESC, p.year DESC
                LIMIT 10
            """, ptId=pt_id)

            papers = [{
                "paperId": record["paperId"],
                "title": record["title"],
                "date": record["date"],
                "abstract": record["abstract"],
                "authors": record["authors"],
                "year": record["year"]
            } for record in result]

            print(papers)

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

        paginator = Paginator(papers, 5)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

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
            "error": f"An error occurred: {str(e)}"
        })
    finally:
        if driver:
            driver.close()