from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from app.utils.neo4j_connection import Neo4jConnection
from app.utils.parse_indonesian_date import parse_indonesian_date
from neo4j_graphrag.embeddings.sentence_transformers import SentenceTransformerEmbeddings
import logging
from app.models import Paper
import ast
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
embedder = SentenceTransformerEmbeddings(model="all-mpnet-base-v2")

def index(request):
    return render(request, "base.html", {
        "content_template": "search-paper/index.html",
        "body_class": "bg-gradient-to-br from-[#c8dcf8] from-5% to-white to-90%",
        "show_search_form": False
    })

def create_search_node(query=""):
    """Buat node query sementara dengan embedding"""
    try:
        # Generate ID unik untuk node query
        paper_id = f"query-{uuid.uuid4()}"
        
        # Generate embedding untuk query
        query_embedding = embedder.embed_query(query)
        logger.info(f"Query embedding generated for: {query}")
        
        # Convert embedding ke format yang benar
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()
        
        # Simpan node query
        paper = Paper(
            paperId=paper_id,
            title=query,
            abstract="Query node for semantic search",
            search_embedding=query_embedding,
        )
        paper.save()
        
        return paper_id
    except Exception as e:
        logger.error(f"Error creating search node: {e}")
        raise

def create_graph_projection(driver):
    with driver.session() as session:
        try:
            # Cek dulu apakah graph sudah ada
            check_result = session.run("CALL gds.graph.exists('myGraph') YIELD exists RETURN exists")
            if check_result.single()["exists"]:
                logger.info("Graph 'myGraph' already exists. Dropping it first...")
                session.run("CALL gds.graph.drop('myGraph')")
            
            # Buat graph projection baru
            result = session.run("""
                MATCH (p:Paper) WHERE p.search_embedding IS NOT NULL
                RETURN gds.graph.project(
                    'myGraph',
                    p,
                    null,
                    {
                        sourceNodeProperties: p { .search_embedding },
                        targetNodeProperties: {}
                    }
                )
            """)

            if result:
                logger.info("Graph projection created successfully")
                return True
            else: 
                logger.error("Failed to create graph projection")
                return False
        except Exception as e:
            logger.error(f"Error creating graph: {e}")
            return False

def delete_query_node(paper_id, driver):
    """Menghapus node user query setelah proses similarity selesai"""
    logger.info(f"Menghapus node query {paper_id}...")
    with driver.session() as session:
        try:
            result = session.run("""
                MATCH (p:Paper {paperId: $paperId})
                DETACH DELETE p
                RETURN count(p) as deleted
            """, paperId=paper_id)
            
            deleted = result.single()["deleted"]
            if deleted > 0:
                logger.info(f"Node query berhasil dihapus.")
            else:
                logger.warning(f"Node query tidak ditemukan atau bukan node user query.")
        except Exception as e:
            logger.error(f"Error deleting query node: {e}")

def search(request):
    try:
        user_query = request.GET.get('query', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        
        if not user_query:
            return render(request, "base.html", {
                "content_template": "search-paper/search-result.html",
                "body_class": "bg-gray-100",
                "show_search_form": True,
                "error": "Please enter a search query"
            })

        # Get Neo4j driver
        neo4j_connection = Neo4jConnection()
        driver = neo4j_connection.get_driver()
        
        # Create search node with embedding
        paper_id = create_search_node(query=user_query)
        
        # Create graph projection
        projection_success = create_graph_projection(driver)
        if not projection_success:
            raise Exception("Failed to create graph projection")
        
        with driver.session() as session:
            keywords = user_query.lower().split()
            params = {"keywords": keywords, "paperId": paper_id}
            
            # Build date filter
            date_filter = ""
            if start_date and end_date:
                try:
                    start_dt = parse_indonesian_date(start_date)
                    end_dt = parse_indonesian_date(end_date)
                    start_str = start_dt.strftime("%Y-%m-%d")
                    end_str = end_dt.strftime("%Y-%m-%d")
                    date_filter = """
                        AND (
                            (recommendedPaper.publicationDate IS NOT NULL AND 
                             left(recommendedPaper.publicationDate, 10) >= $start_date AND
                             left(recommendedPaper.publicationDate, 10) <= $end_date)
                            OR
                            (recommendedPaper.year IS NOT NULL AND 
                             recommendedPaper.year >= $start_year AND
                             recommendedPaper.year <= $end_year)
                        )
                    """
                    params.update({
                        "start_date": start_str,
                        "end_date": end_str,
                        "start_year": start_dt.year,
                        "end_year": end_dt.year
                    })
                except Exception as e:
                    logger.error(f"Error processing dates: {e}")
            
            # Search papers using KNN similarity search
            result = """
                MATCH (p:Paper {paperId: $paperId})
                CALL gds.knn.stream('myGraph', {
                    topK: 1,
                    nodeProperties: ['search_embedding'],
                    concurrency: 4,  
                    sampleRate: 0.8,  
                    deltaThreshold: 0.1  
                })
                YIELD node1, node2, similarity
                WHERE id(p) = node1
                WITH gds.util.asNode(node2) AS recommendedPaper, similarity
                OPTIONAL MATCH (recommendedPaper)-[:AUTHORED_BY]->(author:Author)
                WHERE recommendedPaper.paperId <> $paperId
                """ + date_filter + """
                RETURN 
                    recommendedPaper.paperId AS paperId,
                    recommendedPaper.title AS title, 
                    recommendedPaper.abstract AS abstract,
                    recommendedPaper.publicationDate AS date,
                    recommendedPaper.year AS year,
                    recommendedPaper.citationCount AS citation_count,
                    similarity,
                    collect(DISTINCT author.name) AS authors
                ORDER BY similarity DESC
            """
            
            result = session.run(result, **params)
            
            # Process results
            papers = []
            for record in result:
                try:
                    # Get basic paper info
                    paper_data = {
                        "paperId": record["paperId"],
                        "title": record["title"] or "Untitled",
                        "abstract": record["abstract"] or "",
                        "citation_count": record["citation_count"] or 0,
                        "similarity": record["similarity"],
                        "authors": record["authors"],
                    }
                    
                    # Format date
                    if record["date"]:
                        try:
                            dt = datetime.strptime(record["date"].split()[0], "%Y-%m-%d")
                            paper_data["date"] = dt.strftime("%d %B %Y")
                        except:
                            paper_data["date"] = record["date"]
                    elif record["year"]:
                        paper_data["date"] = str(record["year"])
                    else:
                        paper_data["date"] = "Unknown date"
                    
                    # Add to results
                    papers.append(paper_data)
                
                except Exception as e:
                    logger.error(f"Error processing paper result: {e}")
                    continue
        
        # Clean up

        # Pagination
        paginator = Paginator(papers, 10)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        logger.info(f"Found {len(papers)} papers for query: {user_query}")
        
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "page_obj": page_obj,
            "query": user_query,
            "keywords": keywords,
            "start_date": start_date,
            "end_date": end_date,
            "results_count": len(papers),
        })

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"An error occurred: {str(e)}"
        })
    finally:
        if driver:
            delete_query_node(paper_id, driver)
            driver.close()