from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime
from app.utils.neo4j_connection import get_neo4j_driver
import logging
import ast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def index(request):
    return render(request, "base.html", {
        "content_template": "search-paper/index.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })

def search(request):
    try:
        query = request.GET.get('query', '')
        if not query:
            return render(request, "base.html", {
                "content_template": "search-paper/search-result.html",
                "body_class": "bg-gray-100",
                "show_search_form": True,
                "error": "Please enter a search query"
            })

        # Get Neo4j driver
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            # Get CSO topics
            cso_topics = session.run("""
                MATCH (t:Topic)
                RETURN t.name AS Topic
            """).data()
            cso_topics = [record["Topic"] for record in cso_topics]

            keywords = query.lower().split()  # Simplified for example

            # Search papers
            result = session.run("""
                MATCH (p:Paper)
                WHERE any(keyword IN $keywords WHERE
                    toLower(p.title) CONTAINS toLower(keyword) OR
                    toLower(p.abstract) CONTAINS toLower(keyword) OR
                    any(topic IN p.cso_topics WHERE toLower(topic) CONTAINS toLower(keyword)))
                WITH p, 
                    size([keyword IN $keywords WHERE toLower(p.title) CONTAINS toLower(keyword)]) AS title_matches,
                    size([keyword IN $keywords WHERE 
                        toLower(p.abstract) CONTAINS toLower(keyword) OR 
                        any(topic IN p.cso_topics WHERE toLower(topic) CONTAINS toLower(keyword))]) AS other_matches
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(t:Topic)
                OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
                RETURN p.paperId AS paperId,
                    p.title AS title,
                    p.abstract AS abstract,
                    p.year AS year,
                    collect(DISTINCT author.name) AS authors,
                    p.publicationDate AS date,
                    p.citationCount AS citation_count,
                    p.cso_topics AS topics,
                    collect(DISTINCT t.name) AS related_topics,
                    title_matches,
                    other_matches
                ORDER BY title_matches DESC, citation_count DESC, other_matches DESC
                LIMIT 50
            """, keywords=keywords)

            papers = []
            for record in result:
                try:
                    paper = {
                        "paperId": record["paperId"],
                        "title": record["title"],
                        "abstract": record["abstract"] or "",
                        "authors": record["authors"] or [],
                        "date": record["date"],
                        "year": record["year"],
                        "related_topics": record["related_topics"] or []
                    }
                    
                    # Format date if exists
                    if paper["date"]:
                        dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                        paper["date"] = dt.strftime("%d %B %Y")
                    else:
                        paper["date"] = paper.get("year", "Unknown date")
                        
                    papers.append(paper)
                except Exception as e:
                    logger.error(f"Error processing paper: {e}")
                    continue

        # Close the driver
        driver.close()

        # Pagination
        paginator = Paginator(papers, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        logger.info(f"Found {len(papers)} papers for query: {query}, keywords: {keywords}")

        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "page_obj": page_obj,
            "query": query,
            "keywords": keywords,
        })

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"An error occurred: {str(e)}"
        })
        
def get_paper_detail(request, paper_id):
    try:
        # Get Neo4j driver
        driver = get_neo4j_driver()
        
        with driver.session() as session:
            # Get paper details
            result = session.run("""
                MATCH (p:Paper {paperId: $paperId})
                RETURN p.paperId AS paperId,
                       p.title AS title,
                       p.abstract AS abstract,
                       p.authors AS authors,
                       p.publicationDate AS date,
                       p.externalIds AS externalIds,
                       p.url AS url,
                       p.cso_topics AS topics
            """, paperId=paper_id).single()

            if not result:
                raise Exception("Paper not found")
            
            external_ids = {}
            if result["externalIds"]:
                try:
                    external_ids = ast.literal_eval(result["externalIds"])
                except:
                    external_ids = {}

            paper = {
                "id": result["paperId"],
                "title": result["title"],
                "abstract": result["abstract"] or "",
                "authors": result["authors"] or [],
                "date": result["date"] or "",
                "doi": external_ids.get('DOI', ''),
                "url": result["url"] or "",
            }

            # Format date if exists
            if paper["date"]:
                dt = datetime.strptime(paper["date"], "%Y-%m-%d %H:%M:%S")
                paper["date"] = dt.strftime("%d %B %Y")

            # Dummy related papers for carousel
            paper_recommendation = [
                {
                    "id": "1",
                    "title": "Understanding Deep Learning Requires Rethinking Generalization",
                    "abstract": "Deep learning has achieved remarkable success in many applications...",
                    "authors": ["Zhang, Chiyuan", "Bengio, Samy", "Hardt, Moritz"],
                    "date": "15 March 2024"
                },
                {
                    "id": "2", 
                    "title": "Attention Is All You Need",
                    "abstract": "The dominant sequence transduction models are based on complex recurrent neural networks...",
                    "authors": ["Vaswani, Ashish", "Shazeer, Noam"],
                    "date": "12 March 2024"
                },
                {
                    "id": "3",
                    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                    "abstract": "We introduce a new language representation model called BERT...",
                    "authors": ["Devlin, Jacob", "Chang, Ming-Wei"],
                    "date": "10 March 2024"
                }
            ]

        driver.close()

        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "paper": paper,
            "paper_recommendation": paper_recommendation
        })

    except Exception as e:
        logger.error(f"Error getting paper detail: {str(e)}")
        return render(request, "base.html", {
            "content_template": "detail-paper/index.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"An error occurred: {str(e)}"
        })