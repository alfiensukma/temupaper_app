from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from app.utils.neo4j_connection import Neo4jConnection
from app.utils.parse_indonesian_date import parse_indonesian_date
import logging
import ast

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        
        if not query:
            return render(request, "base.html", {
                "content_template": "search-paper/search-result.html",
                "body_class": "bg-gray-100",
                "show_search_form": True,
                "error": "Please enter a search query"
            })

        # Get Neo4j driver
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()
        
        with driver.session() as session:
            keywords = query.lower().split()
            date_filter = ""
            params = {"keywords": keywords}
            
            # filter date
            if start_date and end_date:
                try:
                    start_dt = parse_indonesian_date(start_date)
                    end_dt = parse_indonesian_date(end_date)
                    start_str = start_dt.strftime("%Y-%m-%d")
                    end_str = end_dt.strftime("%Y-%m-%d")
                    date_filter = """
                        AND left(p.publicationDate, 10) >= $start_date 
                        AND left(p.publicationDate, 10) <= $end_date
                    """
                    params.update({
                        "start_date": start_str,
                        "end_date": end_str
                    })
                except Exception as e:
                    logger.error(f"Error processing dates: {e}")
                    
            # Search papers
            result = session.run(f"""
                MATCH (p:Paper)
                WHERE any(keyword IN $keywords WHERE
                    toLower(p.title) CONTAINS toLower(keyword) OR
                    toLower(p.abstract) CONTAINS toLower(keyword))
                {date_filter}
                WITH p,
                    size([keyword IN $keywords WHERE toLower(p.title) CONTAINS toLower(keyword)]) AS title_matches,
                    size([keyword IN $keywords WHERE toLower(p.abstract) CONTAINS toLower(keyword)]) AS abstract_matches
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(t:Topic)
                WHERE any(keyword IN $keywords WHERE toLower(t.name) CONTAINS toLower(keyword))
                WITH p, 
                    collect(DISTINCT t.name) as related_topics,
                    title_matches,
                    abstract_matches,
                    COALESCE(p.citationCount, 0) as citation_count
                RETURN p.paperId AS paperId,
                       p.title AS title,
                       p.abstract AS abstract,
                       p.authors AS authors,
                       p.publicationDate AS date,
                       related_topics,
                       title_matches,
                       abstract_matches,
                       citation_count
                ORDER BY 
                    title_matches DESC,
                    citation_count DESC,
                    abstract_matches DESC
            """, **params)

            papers = []
            for record in result:
                try:
                    # Fix: Safely handle authors that might be None
                    authors = []
                    if record["authors"] is not None:
                        try:
                            authors = [{"name": author["name"], "id": author["authorId"]} 
                                     for author in record["authors"]]
                        except (TypeError, KeyError) as e:
                            logger.error(f"Error processing authors: {e}")
                    
                    paper = {
                        "paperId": record["paperId"],
                        "title": record["title"],
                        "abstract": record["abstract"] or "",
                        "authors": authors,  # Use processed authors list
                        "date": record["date"] or "",
                        "related_topics": record["related_topics"] or [],
                        "citation_count": record["citation_count"],
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

        logger.info(f"Found {len(papers)} papers for query: {query}")
        
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "page_obj": page_obj,
            "query": query,
            "keywords": keywords,
            "start_date": start_date,
            "end_date": end_date,  
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

            # Fix: Safely handle authors that might be None
            authors = []
            if result["authors"] is not None:
                try:
                    authors = [{"name": author["name"], "id": author["authorId"]} 
                             for author in result["authors"]]
                except (TypeError, KeyError) as e:
                    logger.error(f"Error processing authors in detail: {e}")

            paper = {
                "id": result["paperId"],
                "title": result["title"],
                "abstract": result["abstract"] or "",
                "authors": authors,  # Use processed authors list
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