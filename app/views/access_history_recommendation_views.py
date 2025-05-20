from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime
import logging
from app.utils.neo4j_connection import Neo4jConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def access_history(request):
    user_id = request.session.get('user_id')

    try:
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()

        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {userId: $userId})-[:HAS_READ]->(n:Paper)-[r:HIGHEST_SIMILAR]->(p:Paper)
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    p.title AS title,
                    p.paperId as paperId,
                    p.abstract as abstract, 
                    p.publicationDate AS date,
                    p.year AS year,
                    p.pagerank as pagerank,
                    r.score as score,
                    collect(DISTINCT author.name) AS authors
                ORDER BY r.score DESC, p.pagerank DESC, p.publicationDate DESC
                """,
                userId=user_id
            )

            papers = [{
                "paperId": record["paperId"],
                "title": record["title"],
                "date": record["date"],
                "abstract": record["abstract"],
                "authors": record["authors"],
                "year": record["year"]
            } for record in result]

            # Format tanggal publikasi
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

        paginator = Paginator(papers, 5)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        return render(request, "base.html", {
            "content_template": "access-history-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "papers": papers,
            "page_obj": page_obj,
        })

    except Exception as e:
        logger.error(f"Error in access_history view: {str(e)}")
        return render(request, "base.html", {
            "content_template": "access-history-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        })
    finally:
        if driver:
            driver.close()
