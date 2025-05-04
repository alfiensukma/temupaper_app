from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime
from app.utils.neo4j_connection import get_neo4j_driver
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def similarity_access(request):
    driver = None

    if not request.session.get('is_authenticated', False):
        return render(request, "base.html", {
            "content_template": "peer-institution-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": "Anda perlu login untuk melihat halaman ini"
        })
    
    user_id = request.session.get('user_id')

    try:
        driver = get_neo4j_driver()

        with driver.session() as session:
            graph_exists = session.run("""
                CALL gds.graph.exists('aksesGraph')
                YIELD exists
                RETURN exists
            """).single()["exists"]

        if graph_exists:
            with driver.session() as session:
                session.run("""
                    CALL gds.graph.drop('aksesGraph', false)
                    YIELD graphName
                    RETURN graphName
                """)
                print("Existing 'aksesGraph' dropped.")

        # Create the graph projection with only nodes having embeddings
        with driver.session() as session:
            session.run("""
                MATCH (source:User)
                OPTIONAL MATCH (source)-[r:HAS_READ]->(target:Paper)
                RETURN gds.graph.project(
                    'aksesGraph',
                    source,
                    target
                )
            """)
            print("Graph 'aksesGraph' created, excluding papers without embeddings.")

        with driver.session() as session:
            result = session.run("""
                MATCH (targetUser:User {userId: $userId})
                CALL gds.nodeSimilarity.stream('aksesGraph')
                YIELD node1, node2, similarity
                WITH gds.util.asNode(node1) AS user1, gds.util.asNode(node2) AS user2, similarity
                WHERE user1.userId = targetUser.userId
                WITH user2, similarity
                ORDER BY similarity DESC
                LIMIT 5
                                 
                MATCH (user2)-[:HAS_READ]->(paper:Paper)
                WHERE NOT EXISTS {
                MATCH (targetUser:User {userId: $userId})-[:HAS_READ]->(paper)}

                WITH paper, COUNT(user2) AS frequency, SUM(similarity) AS totalSimilarity
                OPTIONAL MATCH (paper)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    paper.title AS title,
                    paper.paperId AS paperId,
                    paper.publicationDate AS date,
                    paper.abstract AS abstract,
                    paper.year AS year,
                    frequency AS RecommendedByCount, 
                    totalSimilarity AS SimilarityScore,
                    totalSimilarity / frequency AS AverageSimilarity,
                    collect(DISTINCT author.name) AS authors
                ORDER BY SimilarityScore DESC, frequency DESC
                LIMIT 10
            """, userId=user_id)

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
            "content_template": "similarity-access-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "page_obj": page_obj,
        })
    
    except Exception as e:
        logger.error(f"Error in similarity view: {str(e)}")
        return render(request, "base.html", {
            "content_template": "similarity-access-recommendation/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": f"An error occurred: {str(e)}"
        })
    finally:
        if driver:
            driver.close()

    