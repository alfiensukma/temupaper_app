import json
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

# Helper functions for search functionality
def prepare_search_params(request):
    """Prepare and validate search parameters from request"""
    user_query = request.GET.get('query', '').strip()
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    return {
        'query': user_query,
        'start_date': start_date,
        'end_date': end_date,
        'page': request.GET.get("page", 1)
    }

def build_date_filter(start_date, end_date):
    """Build date filter for Cypher query"""
    date_filter = ""
    params = {}
    
    if start_date and end_date:
        try:
            date_filter = """
                AND (
                    CASE
                        WHEN paper.publicationDate IS NOT NULL THEN
                            CASE 
                                WHEN paper.publicationDate CONTAINS '/' 
                                THEN toInteger(split(split(paper.publicationDate, ' ')[0], '/')[2]) >= $start_year
                                     AND toInteger(split(split(paper.publicationDate, ' ')[0], '/')[2]) <= $end_year
                                WHEN paper.publicationDate CONTAINS '-' 
                                THEN toInteger(split(paper.publicationDate, '-')[0]) >= $start_year
                                     AND toInteger(split(paper.publicationDate, '-')[0]) <= $end_year
                                ELSE false
                            END
                        WHEN paper.year IS NOT NULL THEN
                            toInteger(paper.year) >= $start_year AND toInteger(paper.year) <= $end_year
                        ELSE false
                    END
                )
            """
            
            params = {
                "start_year": int(start_date),
                "end_year": int(end_date)
            }
            logger.info(f"Applied date filter: {start_date} to {end_date}")
            
        except Exception as e:
            logger.error(f"Error building date filter: {str(e)}")
            return "", {}
    
    return date_filter, params

def find_seed_papers(session, paper_id, date_filter, params):
    """Find initial seed papers using KNN similarity search"""

    print(f"Seed paper IDs: {paper_id}")

    logger.info(f"Running KNN query with params: {params}")
    knn_query = """
        MATCH (p:Paper {paperId: $paperId})
        CALL gds.knn.stream('myGraph', {
            topK: 10,
            nodeProperties: ['search_embedding'],
            randomSeed: 42,
            concurrency: 1,
            sampleRate: 1.0,
            deltaThreshold: 0.1
        })
        YIELD node1, node2, similarity
        WHERE node1 = id(p)
        """ + date_filter + """
        WITH gds.util.asNode(node2) AS paper, similarity
        RETURN paper.paperId AS paperId, similarity AS knn_similarity
        ORDER BY knn_similarity DESC
        LIMIT 1
    """
    
    knn_results = session.run(knn_query, **params)
    seed_paper_ids = [record["paperId"] for record in knn_results]
    logger.info(f"Found {len(seed_paper_ids)} seed papers")
    
    return seed_paper_ids

def find_similar_papers(session, seed_paper_ids, date_filter, params):
    """Find papers similar to seed papers"""
    if not seed_paper_ids:
        return [], []
    
    # Get details of seed papers
    knn_detail_query = """
        UNWIND $paperIds AS knnPaperId
        MATCH (p:Paper {paperId: knnPaperId})
        OPTIONAL MATCH (p)-[:AUTHORED_BY]->(author:Author)
        RETURN 
            p.paperId AS paperId,
            p.title AS title, 
            p.abstract AS abstract,
            p.publicationDate AS date,
            p.year AS year,
            p.citationCount AS citation_count,
            1.0 AS similarity_score,
            collect(DISTINCT author.name) AS authors
    """
    
    knn_details = session.run(knn_detail_query, paperIds=seed_paper_ids)
    
    # Print or log the titles of seed papers
    logger.info("Seed paper titles:")
    for record in knn_details:
        logger.info(f"Title: {record['title']}")
    
    # Reset the cursor for knn_details to be used later
    knn_details = session.run(knn_detail_query, paperIds=seed_paper_ids)
    
    # Get papers similar to seed papers
    similar_query = """
        UNWIND $paperIds AS topPaperId
        MATCH (top:Paper {paperId: topPaperId})
        OPTIONAL MATCH (top)-[r:SIMILAR]->(paper:Paper)
        WHERE 1=1 """ + date_filter + """
        OPTIONAL MATCH (paper)-[:AUTHORED_BY]->(author:Author)
        RETURN 
            paper.paperId AS paperId,
            paper.title AS title, 
            paper.abstract AS abstract,
            paper.publicationDate AS date,
            paper.year AS year,
            paper.citationCount AS citation_count,
            paper.pagerank AS pagerank,
            r.score AS similarity_score,
            collect(DISTINCT author.name) AS authors
        ORDER BY similarity_score DESC, paper.pagerank DESC
        LIMIT 20
    """
    
    similar_results = session.run(similar_query, paperIds=seed_paper_ids, **params)
    
    return knn_details, similar_results

def format_paper_data(record, is_seed=False):
    """Format paper data from Neo4j record to dictionary"""
    paper_id_result = record["paperId"]
    
    paper_data = {
        "paperId": paper_id_result,
        "title": record["title"] or "Untitled",
        "abstract": record["abstract"] or "",
        "citation_count": record["citation_count"] or 0,
        "similarity": record["similarity_score"],
        "authors": record["authors"],
        "date": record["date"],
        "year": record["year"],
        "is_seed": is_seed
    }

    if record["date"]:
        try:
            date_str = record["date"]
            
            # Handle date format "m/d/yyyy 0:00" or "m/d/yyyy"
            if '/' in date_str:
                date_str = date_str.split()[0]
                month, day, year = map(int, date_str.split('/'))
                dt = datetime(year, month, day)
                paper_data["date"] = dt.strftime("%d %B %Y")
            
            # Handle date format "yyyy-mm-dd"
            elif '-' in date_str:
                dt = datetime.strptime(date_str.split()[0], "%Y-%m-%d")
                paper_data["date"] = dt.strftime("%d %B %Y")
            
            else:
                paper_data["date"] = date_str
                
        except Exception as e:
            logger.error(f"Error formatting date '{record['date']}': {str(e)}")
            paper_data["date"] = record["date"]
            
    elif record["year"]:
        paper_data["date"] = str(record["year"])
    else:
        paper_data["date"] = record.get("year", "Unknown date")
    
    return paper_data

def process_search_results(knn_details, similar_results):
    """Process search results and remove duplicates"""
    papers = []
    seen_ids = set()
    
    # Process KNN results (seed papers)
    for record in knn_details:
        paper_id = record["paperId"]
        if paper_id not in seen_ids:
            seen_ids.add(paper_id)
            papers.append(format_paper_data(record, is_seed=True))
    
    # Process similar papers
    for record in similar_results:
        paper_id = record["paperId"]
        if paper_id not in seen_ids:
            seen_ids.add(paper_id)
            papers.append(format_paper_data(record, is_seed=False))
    
    # Sort by similarity score, handle None values
    papers.sort(key=lambda x: x["similarity"] if x["similarity"] is not None else 0.0, reverse=True)
    
    return papers

# Main search function
def search(request):
    query = request.GET.get('query', '').strip()
    paper_id = None
    driver = None
    
    if request.GET.get('state') != 'loaded':
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "query": query,
            "is_loading": True,
            "body_class": "bg-gray-100",
            "show_search_form": True
        })
    
    try:
        # Prepare search parameters
        search_params = prepare_search_params(request)
        
        if not search_params['query']:
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
        paper_id = create_search_node(query=search_params['query'])
        
        # Create graph projection
        projection_success = create_graph_projection(driver)
        if not projection_success:
            raise Exception("Failed to create graph projection")
        
        with driver.session() as session:
            # Build query parameters
            date_filter, date_params = build_date_filter(
                search_params['start_date'], 
                search_params['end_date']
            )
            
            params = {
                "paperId": paper_id,
                **date_params
            }
            
            # Find seed papers using KNN
            seed_paper_ids = find_seed_papers(session, paper_id, date_filter, params)
            
            if not seed_paper_ids:
                return render(request, "base.html", {
                    "content_template": "search-paper/search-result.html",
                    "body_class": "bg-gray-100", 
                    "show_search_form": True,
                    "error": "No results found for your query"
                })
            
            # Find similar papers
            knn_details, similar_results = find_similar_papers(
                session, seed_paper_ids, date_filter, params
            )
            
            # Process and combine results
            papers = process_search_results(knn_details, similar_results)
        
        # Pagination
        paginator = Paginator(papers, 10)
        page_obj = paginator.get_page(search_params['page'])

        logger.info(f"Found {len(papers)} papers for query: {search_params['query']}")
        
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "page_obj": page_obj,
            "query": search_params['query'],
            "start_date": search_params['start_date'],
            "end_date": search_params['end_date'],
            "results_count": len(papers),
            "is_loading": False
        })

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return render(request, "base.html", {
            "content_template": "search-paper/search-result.html",
            "body_class": "bg-gray-100",
            "show_search_form": True,
            "error": f"An error occurred: {str(e)}",
            "is_loading": False
        })
    finally:
        # Clean up resources
        if paper_id and driver:
            delete_query_node(paper_id, driver)
        if driver:
            driver.close()