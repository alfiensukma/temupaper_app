from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime
from app.utils.neo4j_connection import Neo4jConnection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def topic_list(request):
    topic = [
        {"name": "Artificial Intelligence", "id": "18"},
        {"name": "Bioinformatics", "id": "47"},
        {"name": "Computer Aided Design", "id": "119"},
        {"name": "Computer Hardware", "id": "131"},
        {"name": "Computer Imaging and Vision", "id": "132"},
        {"name": "Computer Networks", "id": "138"},
        {"name": "Computer Programming", "id": "141"},
        {"name": "Computer Security", "id": "144"},
        {"name": "Computer Systems", "id": "148"},
        {"name": "Data Mining", "id": "176"},
        {"name": "Human Computer Interaction", "id": "319"},
        {"name": "Information Retrieval", "id": "343"},
        {"name": "Information Technology", "id": "349"},
        {"name": "Internet", "id": "361"},
        {"name": "Operating Systems", "id": "466"},
        {"name": "Pattern Matching", "id": "478"},
        {"name": "Robotics", "id": "529"},
        {"name": "Software", "id": "549"},
        {"name": "Software Engineering", "id": "554"},
        {"name": "Theoretical Computer Science", "id": "600"},
    ]

    return render(request, "base.html", {
        "content_template": "topic-recommendation/index.html",
        "body_class": "bg-gray-100",
        "show_search_form": False,
        "topic": topic,
    })
    
def topic_result(request, topic):
    driver = None

    try:
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()

        with driver.session() as session:
            # Dapatkan nama topik dari database
            topic_name_result = session.run("""
                MATCH (t:Topic {id: $topicId})
                RETURN t.name AS topic_name
            """, topicId=topic)
            
            # Ekstrak nama topik dari hasil query
            topic_record = topic_name_result.single()
            
            if topic_record and topic_record.get("topic_name"):
                topic_name = topic_record["topic_name"]
                topic_name = ' '.join(word.capitalize() for word in str(topic_name).split('_'))

            # Query utama untuk paper
            result = session.run("""
                MATCH (root:Topic {id: $topicId})
                MATCH (subtopic:Topic)-[:SUB_TOPIC_OF*0..]->(root)
                MATCH (paper:Paper)-[:IS_ABOUT]->(subtopic)
                OPTIONAL MATCH (paper)-[:AUTHORED_BY]->(author:Author)
                RETURN 
                    paper.title AS title, 
                    paper.citationCount AS citation_count,
                    paper.paperId as paperId,
                    paper.abstract as abstract,
                    paper.publicationDate AS date,
                    paper.year AS year,
                    collect(DISTINCT author.name) AS authors  
                ORDER BY citation_count DESC,  paper.publicationDate DESC
                LIMIT 10
            """, topicId=topic)

            # Transformasi data hasil query
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

        paginator = Paginator(papers, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        return render(request, "base.html", {
            "content_template": "topic-recommendation/topic-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "page_obj": page_obj,
            "selected_topic": topic_name,
            "selected_topic_id": topic,
        })
    
    except Exception as e:
        logger.error(f"Error in topic_result view: {str(e)}")
        return render(request, "base.html", {
            "content_template": "topic-recommendation/topic-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        })
    finally:
        if driver:
            driver.close()